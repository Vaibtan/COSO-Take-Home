# Q1 Architecture

This document describes the technical design for Q1: a cited RAG service over
messy construction PDFs. It is derived from `Q1_CANDIDATE_BRIEF.md` and
`design-decisions.md`.

Use this document for **what the system will build and how the major modules
fit together**. Use `design-decisions.md` for rationale and
`IMPLEMENTATION-PLAN.md` for the coding checklist.

## Problem Statement

COSO users need reliable answers from infrastructure tender, RFP, corrigendum,
BOQ, and safety documents. The hard part is not just finding plausible text. The
system must answer with traceable citations, avoid unsupported claims, handle
scanned and table-heavy PDFs, and make temporal conflicts visible instead of
returning a randomly ranked obsolete value.

The judged priorities are:

1. Citation integrity.
2. Problem A failure analysis quality.
3. Refusal quality.
4. Problem B conflict-over-time handling.
5. Problem C production-style eval design.
6. Code quality and typing.

## Solution

Build a FastAPI service backed by Docker-only Postgres 16 and pgvector. The
service ingests all PDFs from `q1/`, stores page-aware chunks and a narrow
IN-09 conflict sidecar, and serves `POST /query` as an SSE stream.

The implementation has two reproducible modes:

- `baseline`: naive but realistic RAG for failure demonstration.
- `fixed`: accuracy-first RAG with hybrid retrieval, evidence selection,
  citation verification, conservative refusal, targeted OCR/table fallback, and
  IN-09 conflict resolution.

Model/provider defaults are defined in `design-decisions.md`. The architecture
assumes `gemini-3-flash-preview` for generation, extraction, evidence selection, and
judging, with `gemini-embedding-2` at 768 dimensions for retrieval.

## System Components

### API Layer

FastAPI exposes:

- `GET /healthz`: reports API, DB, and ingestion readiness.
- `POST /ingest?force=false`: runs ingestion or skips unchanged corpus content.
- `POST /query`: accepts a question and optional mode, then streams SSE events.
- `POST /eval/run`: runs baseline/fixed evals over the configured query set.

`POST /query` request shape:

```json
{
  "question": "What is the bid validity period for the JNPT maintenance tender?",
  "mode": "fixed"
}
```

SSE event types:

- `status`: progress messages such as retrieval, reranking, verification.
- `retrieved_evidence`: cited chunks selected for the answer.
- `answer_delta`: validated answer text chunks.
- `refusal`: refusal reason and closest evidence where useful.
- `done`: terminal success event.
- `error`: terminal error event.

### Ingestion Pipeline

Ingestion is page-first and provenance-preserving.

1. Discover PDFs under `q1/`.
2. Hash each PDF and compare with the stored ingestion manifest.
3. Extract local text and tables first.
4. Detect weak pages using heuristics such as low character count, poor text
   density, or table-critical document patterns.
5. Use Gemini OCR/table fallback only for query-relevant weak pages or failed
   retrieval cases.
6. Create page-aware chunks with stable chunk IDs, filename, page number,
   extraction method, text, and metadata.
7. Embed chunks with Gemini embeddings.
8. Extract IN-09 conflict facts from the three IN-09 corrigenda.

The baseline mode uses only local extraction where available. The fixed mode can
use targeted Gemini extraction fallback.

Chunking defaults:

- Never split across PDF page boundaries.
- Target about 800 tokens per chunk with about 100 tokens of overlap.
- Prefer paragraph/list boundaries over fixed-width splitting.
- Keep table pages whole up to about 1500 tokens; split larger tables by row
  groups while preserving headers.

### Storage Model

Postgres stores:

- Corpus manifest: document path, hash, ingestion version, timestamps.
- Documents: filename, inferred document type, tender/package identifiers.
- Pages: document ID, page number, extraction method, raw page text.
- Chunks: page ID, chunk text, token estimate, metadata, `vector(768)`
  embedding.
- Lexical index fields: generated `tsvector` column for Postgres full-text
  retrieval, indexed with GIN and ranked with `ts_rank_cd`.
- Conflict facts: normalized tender/package ID, corrigendum number/date, field
  name, field value, source chunk, confidence.
- Eval runs: query ID, mode, retrieved evidence, answer, refusal, metrics.

### Baseline Query Flow

Baseline flow:

1. Embed the question with Gemini embeddings.
2. Retrieve top-k chunks using vector similarity.
3. Pass retrieved chunks to `gemini-3-flash-preview` for answer generation.
4. Require inline citations in the prompt, but do not run a separate reranker,
   verifier, conflict resolver, or OCR fallback.

There is no reranker in baseline mode.

### Fixed Query Flow

Fixed-mode flow:

1. Retrieve a broad candidate set using Postgres full-text search plus pgvector
   similarity search.
2. Use `gemini-3-flash-preview` as an evidence selector/reranker over candidate
   chunks.
3. Detect whether the question triggers IN-09 conflict sidecar logic.
4. Generate a structured answer draft with sentence-level citations.
5. Verify cited claims against the selected evidence.
6. Repair unsupported claims once if the verifier finds fixable issues.
7. Refuse if evidence remains insufficient or citations fail validation.
8. Stream the validated answer via SSE.

The fixed pipeline uses a reranker: `gemini-3-flash-preview` evidence selection
after broad hybrid retrieval.

### Citation Contract

Every factual sentence must end with one or more citations:

```text
The bid validity period is 120 days from the bid due date. [coso-corpus-17-nhai-rfp783-jnpt.pdf p.34]
```

The verifier checks:

- Cited filename exists in the corpus.
- Cited page exists for that file.
- The citation maps to one of the selected chunks.
- The cited text supports the sentence closely enough for this domain.

If a claim is not supported, the fixed pipeline repairs or refuses.

### Refusal Policy

The fixed pipeline refuses when:

- Retrieval returns no sufficiently relevant evidence.
- The evidence selector cannot identify supporting chunks.
- Citation verification fails after one repair attempt.
- The answer depends on an unresolved conflict that cannot be ordered by
  document metadata.

Refusals should be short, explain the evidence problem, and cite closest
evidence when that helps the user understand the boundary.

### IN-09 Conflict Sidecar

The conflict sidecar is a narrow typed fact store, not a full knowledge graph
product. It initially extracts facts only from the three IN-09 corrigenda:

- Tender/package IDs.
- Corrigendum number and date.
- Last-date-for-addendum fields.
- Source chunk citations for each extracted value.

The main use cases are:

- Resolve the IN-09 conflict-over-time problem.
- Provide a small KG-style benchmark against evidence-first RAG.

For IN-09 conflicts, latest authoritative corrigendum wins, and superseded
conflicting values are disclosed with citations.

### Eval Harness

The eval harness uses the provided 15 baseline queries as the backbone and
labels at least 10 golden cases.

Metrics:

- Retrieval recall at k against gold evidence.
- Citation validity.
- Citation support.
- Refusal correctness for weak-evidence cases.
- Conflict handling correctness for IN-09.
- LLM-as-judge answer quality as a warning signal only.

CI hard-fails deterministic gates:

- Invalid citation format or nonexistent source.
- Gold evidence missing from top-k for labeled queries.
- Citation-support regression below threshold.
- Schema or API contract errors.

LLM judge scores and human quality ratings are reported but do not block CI.

## Module Boundaries

The implementation should keep these as deep modules with narrow interfaces:

- Configuration: env parsing and model/database settings.
- Database access: migrations, sessions, and repository methods.
- Ingestion: PDF discovery, extraction, chunking, embedding, manifest updates.
- Retrieval: baseline vector search and fixed hybrid candidate retrieval.
- Evidence selection: Gemini reranking for fixed mode only.
- Answering: prompt construction, structured answer generation, and SSE output.
- Verification: citation parsing, source checks, support checks, repair/refusal.
- Conflict sidecar: IN-09 fact extraction, normalization, and conflict
  resolution.
- Evals: query execution, metrics, golden fixtures, and report generation.

## Test Surfaces

Tests should exercise external behavior and contracts:

- API request/response schemas and SSE event formatting.
- Ingestion idempotency using manifest hashes.
- Citation parser and citation existence checks.
- Refusal behavior when retrieval evidence is empty.
- Baseline vs fixed mode routing.
- IN-09 conflict resolver ordering with controlled fixture facts.
- Eval metric calculation for deterministic gates.

## Out of Scope

- Frontend.
- Authentication and authorization.
- Sub-second latency.
- Full knowledge-graph-first RAG.
- Comprehensive domain ontology.
- Local-only offline mode.
- Perfect OCR for every page.
