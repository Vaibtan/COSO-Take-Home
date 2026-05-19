# Q1 Implementation Plan

This checklist breaks the Q1 architecture into vertical slices. Each slice
should leave the system in a runnable or inspectable state and should preserve
the decisions in `design-decisions.md` and `Q1-ARCHITECTURE.md`.

Use this document for **what to code and verify next**. It intentionally avoids
re-explaining architecture decisions; follow `Q1-ARCHITECTURE.md` for system
design and `design-decisions.md` for rationale.

## Slice 1: Service Skeleton and Runtime

**Type:** AFK  
**Blocked by:** None  

### What to build

Create the FastAPI application, configuration layer, Docker Compose stack,
Postgres 16 with pgvector, and health check path.

### Acceptance criteria

- [ ] `docker compose up` starts Postgres and the API.
- [ ] `GET /healthz` reports API and DB readiness.
- [ ] App configuration reads Gemini, DB, model, and corpus settings from env.
- [ ] Project has a clear Python package layout and dependency file.
- [ ] README contains initial run instructions and required env vars.

## Slice 2: Database Schema and Migrations

**Type:** AFK  
**Blocked by:** Slice 1  

### What to build

Add schema support for corpus manifests, documents, pages, chunks, embeddings,
KG facts, and eval runs.

### Acceptance criteria

- [ ] Migrations create pgvector extension and all Q1 tables.
- [ ] Chunks store filename, page number, text, metadata, and embedding vector.
- [ ] Corpus manifest stores document hash and ingestion version.
- [ ] KG facts can reference source chunks.
- [ ] Eval run records can store query ID, mode, answer, evidence, and metrics.

## Slice 3: Baseline Ingestion

**Type:** AFK  
**Blocked by:** Slice 2  

### What to build

Implement local PDF extraction, simple page-aware chunking, Gemini embeddings,
and idempotent startup ingestion.

### Acceptance criteria

- [ ] Startup ingestion discovers all PDFs in `q1/`.
- [ ] `POST /ingest?force=false` skips unchanged documents.
- [ ] `POST /ingest?force=true` rebuilds indexed corpus data.
- [ ] Baseline chunks preserve filename and page number.
- [ ] Baseline does not use OCR fallback, reranking, verifier, or KG conflict
      resolution.

## Slice 4: Baseline Query Path

**Type:** AFK  
**Blocked by:** Slice 3  

### What to build

Implement `POST /query` in `baseline` mode with vector top-k retrieval and
Gemini Flash answer generation.

### Acceptance criteria

- [ ] Request accepts `question` and optional `mode`.
- [ ] Baseline mode retrieves chunks by embedding similarity only.
- [ ] Baseline mode has no reranker.
- [ ] Response streams valid SSE events.
- [ ] Answer prompt asks for sentence-level citations.
- [ ] Retrieved evidence is included in the stream for debugging.

## Slice 5: Eval Runner Foundation

**Type:** AFK  
**Blocked by:** Slice 4  

### What to build

Load `q1/baseline_queries.json`, run all 15 queries in baseline mode, persist
outputs, and produce a raw result summary.

### Acceptance criteria

- [ ] `POST /eval/run` can run the provided 15 queries.
- [ ] Results include answer text, citations, retrieved chunks, refusal state,
      and runtime metadata.
- [ ] Outputs are saved locally in a gitignored run directory.
- [ ] A small committed summary format is defined for Problem A writeup input.

## Slice 6: Hybrid Retrieval for Fixed Mode

**Type:** AFK  
**Blocked by:** Slice 4  

### What to build

Add fixed-mode broad retrieval using lexical search plus vector search, with
merged and deduplicated candidate chunks.

### Acceptance criteria

- [ ] Fixed mode retrieves from both lexical and vector signals.
- [ ] Candidate chunks are deduplicated by stable chunk ID.
- [ ] Retrieval scores and source reasons are stored in debug metadata.
- [ ] Baseline retrieval behavior remains unchanged.

## Slice 7: Gemini Evidence Selector/Reranker

**Type:** AFK  
**Blocked by:** Slice 6  

### What to build

Use Gemini Flash to select and rank supporting evidence from the fixed-mode
candidate set before answer generation.

### Acceptance criteria

- [ ] Fixed mode uses the evidence selector after broad hybrid retrieval.
- [ ] Selector output references only provided chunk IDs.
- [ ] Selected evidence is streamed as `retrieved_evidence`.
- [ ] Fixed mode clearly differs from baseline: baseline has no reranker,
      fixed has Gemini evidence selection.

## Slice 8: Citation Verification and Refusal

**Type:** AFK  
**Blocked by:** Slice 7  

### What to build

Implement citation parsing, source existence checks, support verification, one
repair attempt, and conservative refusal.

### Acceptance criteria

- [ ] Every factual sentence in fixed-mode answers has inline citations.
- [ ] Invalid filenames, pages, or unsupported citations fail verification.
- [ ] Fixed mode repairs unsupported claims once when possible.
- [ ] Fixed mode refuses when evidence remains insufficient.
- [ ] Refusals stream as `refusal` events rather than unsupported answers.

## Slice 9: Targeted Gemini OCR and Table Fallback

**Type:** AFK  
**Blocked by:** Slice 3  

### What to build

Add fixed-mode ingestion fallback for low-text, scanned, and table-critical
pages using Gemini.

### Acceptance criteria

- [ ] Local extraction runs first.
- [ ] Weak pages are detected with deterministic heuristics.
- [ ] Gemini fallback stores extraction method metadata.
- [ ] Fallback preserves filename and page number.
- [ ] Baseline ingestion remains local-only.

## Slice 10: KG Sidecar Fact Extraction

**Type:** AFK  
**Blocked by:** Slice 9  

### What to build

Extract typed tender/date/fact records from chunks and store them with source
citations.

### Acceptance criteria

- [ ] KG facts include tender/package IDs, document type, corrigendum metadata,
      deadlines, requirements, quantities, and source chunk IDs.
- [ ] Facts are queryable by normalized tender/package ID and fact type.
- [ ] Fact extraction stores confidence and source provenance.
- [ ] KG sidecar can be benchmarked separately from evidence-first retrieval.

## Slice 11: IN-09 Conflict Resolver

**Type:** AFK  
**Blocked by:** Slice 10  

### What to build

Implement latest-authoritative-corrigendum resolution for the IN-09 addendum
date question, including superseded value disclosure.

### Acceptance criteria

- [ ] Baseline mode can demonstrate random or obsolete IN-09 conflict behavior.
- [ ] Fixed mode identifies multiple conflicting IN-09 values.
- [ ] Fixed mode answers with the latest authoritative corrigendum.
- [ ] Fixed mode cites the winning value and superseded values.
- [ ] Problem B has enough captured output to support the writeup.

## Slice 12: Deterministic Eval Gates

**Type:** AFK  
**Blocked by:** Slice 8  

### What to build

Implement deterministic eval metrics and golden fixtures for at least 10 of the
provided 15 queries.

### Acceptance criteria

- [ ] Golden fixture records expected source evidence for at least 10 queries.
- [ ] Eval reports retrieval recall at k.
- [ ] Eval reports citation validity and citation support.
- [ ] Eval reports refusal correctness where applicable.
- [ ] Deterministic gate failures are machine-readable.
- [ ] LLM judge scores are warnings only, not hard failures.

## Slice 13: Problem A Artifacts

**Type:** HITL  
**Blocked by:** Slices 5, 8, 12  

### What to build

Run baseline and fixed evals, categorize all 15 query outcomes, identify the two
most production-critical failure modes, and document the implemented fix.

### Acceptance criteria

- [ ] Problem A writeup includes result and citations for each query.
- [ ] Each query is categorized using defined failure categories.
- [ ] The two most important production failure modes are defended with cost,
      frequency, severity, and user-impact reasoning.
- [ ] Citation grounding/refusal is shown before and after.
- [ ] Raw run artifacts remain gitignored; concise summaries are committed.

## Slice 14: Problem B Artifacts

**Type:** HITL  
**Blocked by:** Slice 11  

### What to build

Document the baseline IN-09 failure, compare three conflict-handling approaches,
show the implemented fixed behavior, and write the one-week extension note.

### Acceptance criteria

- [ ] Baseline output demonstrates the conflict-over-time failure.
- [ ] Three approaches are compared on cost, latency, UX, and complexity.
- [ ] Chosen latest-authoritative approach is defended.
- [ ] Fixed output cites the current and superseded values.
- [ ] One-week extension paragraph is included.

## Slice 15: Problem C Artifacts

**Type:** HITL  
**Blocked by:** Slice 12  

### What to build

Write the production eval design and include a runnable demo over at least 10
queries.

### Acceptance criteria

- [ ] Metrics are justified for COSO's construction-document RAG problem.
- [ ] BLEU/ROUGE-style metrics are explicitly rejected as primary measures.
- [ ] Golden-set creation avoids burning a domain expert's week.
- [ ] CI hard-fail and warning signals are documented.
- [ ] Demo eval output over at least 10 queries is included.

## Slice 16: README and Submission Polish

**Type:** HITL  
**Blocked by:** Slices 13, 14, 15  

### What to build

Finalize README and submission-facing documentation.

### Acceptance criteria

- [ ] README explains setup, env vars, ingestion, querying, and evals.
- [ ] README includes the required section: `What I used AI tools for, and
      where I overrode them.`
- [ ] README explains Gemini substitution for Anthropic.
- [ ] README links to Problem A/B/C writeups.
- [ ] README explains baseline vs fixed mode.
- [ ] `design-decisions.md`, `Q1-ARCHITECTURE.md`, and
      `IMPLEMENTATION-PLAN.md` are consistent.

## Dependency Order

1. Slice 1: Service Skeleton and Runtime
2. Slice 2: Database Schema and Migrations
3. Slice 3: Baseline Ingestion
4. Slice 4: Baseline Query Path
5. Slice 5: Eval Runner Foundation
6. Slice 6: Hybrid Retrieval for Fixed Mode
7. Slice 7: Gemini Evidence Selector/Reranker
8. Slice 8: Citation Verification and Refusal
9. Slice 9: Targeted Gemini OCR and Table Fallback
10. Slice 10: KG Sidecar Fact Extraction
11. Slice 11: IN-09 Conflict Resolver
12. Slice 12: Deterministic Eval Gates
13. Slice 13: Problem A Artifacts
14. Slice 14: Problem B Artifacts
15. Slice 15: Problem C Artifacts
16. Slice 16: README and Submission Polish
