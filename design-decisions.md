# Q1 Design Decisions

This document records the design decisions made for `Q1_CANDIDATE_BRIEF.md`
before implementation. The guiding priority is accuracy first, especially
citation integrity and refusal quality. Latency and cost matter, but they are
secondary for this take-home.

Use this document for **why** decisions were made. Use `Q1-ARCHITECTURE.md`
for the system design and `IMPLEMENTATION-PLAN.md` for the coding checklist.

## Decision Log

### 1. Use the Gemini ecosystem instead of Anthropic

**Decision:** Use Gemini APIs for extraction support, embeddings, generation,
reranking/evidence selection, and evaluation support.

**Reason:** The brief asks for Anthropic, but the implementation will be run
with available Gemini credits. Keeping one model ecosystem reduces integration
surface area and avoids splitting API credentials, rate limits, model behavior,
and observability across providers.

### 2. Use hybrid ingestion with targeted Gemini OCR/table fallback

**Decision:** Extract text and tables locally first, then use Gemini only for
query-relevant low-text, scanned, or table-critical pages.

**Reason:** The corpus includes clean PDFs, scanned DGMS documents, BOQs, and
corrigenda. Local extraction is cheaper, more deterministic, and preserves page
provenance well. Gemini fallback is reserved for fixed-mode pages that matter
to the 15-query evaluation or to failed retrieval cases, so large scanned PDFs
do not turn into uncontrolled OCR cost.

### 3. Make evidence-first hybrid RAG the main architecture

**Decision:** Build the main answer path around page-aware chunks, lexical plus
vector retrieval, evidence selection, citation verification, and conservative
refusal.

**Reason:** The brief explicitly prioritizes citation integrity over fancy
retrieval. Evidence-first RAG keeps answers grounded in inspectable chunks and
makes failures easier to analyze. It is also a better fit for the required
before/after evaluation than a large, opaque agent workflow.

### 4. Add an IN-09-first conflict sidecar, not a full KG-first pipeline

**Decision:** Build a narrow typed fact/event sidecar for the IN-09
corrigendum conflict first, while keeping evidence-first RAG as the production
answer path.

**Reason:** A full knowledge-graph-first RAG system would be interesting, but
it is too much implementation risk for the take-home. The judged KG-like need
is Problem B: ordering the three IN-09 corrigenda and citing superseded values.
General tender/fact extraction can be deferred unless the evals show it is
needed.

### 5. Use sentence-level inline citations

**Decision:** Every factual sentence in the answer should end with one or more
citations in the form `[filename p.N]`.

**Reason:** The brief says every claim must cite a source chunk. Sentence-level
citations are stricter than paragraph-level citations and easier for reviewers
to manually verify.

### 6. Stream with SSE status events before validated answer text

**Decision:** `/query` should return `text/event-stream` with typed events such
as `status`, `retrieved_evidence`, `answer_delta`, `refusal`, `done`, and
`error`.

**Reason:** Raw token streaming is risky because unsupported claims could reach
the user before verification. SSE lets the service stream progress and evidence
metadata first, then stream only the final validated answer text.

### 7. Resolve IN-09 conflicts using latest authoritative corrigendum

**Decision:** For conflicting fields across IN-09 corrigenda, answer with the
latest applicable corrigendum and disclose superseded conflicting values with
citations.

**Reason:** Returning one randomly ranked corrigendum is confidently wrong.
Only showing conflicts is safe but less useful when the document sequence is
clear. Latest-authoritative resolution gives a practical answer while preserving
traceability.

### 8. Keep runnable `baseline` and `fixed` modes

**Decision:** Implement versioned modes so the same service can run both the
baseline and improved pipeline.

**Reason:** Problems A and B require demonstrating failures before fixes.
Versioned modes make the before/after comparison reproducible instead of
depending on old logs or git snapshots.

### 9. Define the baseline as naive but realistic

**Decision:** The baseline uses local extraction where available, simple
page-aware chunks, Gemini embeddings, vector top-k retrieval, and Gemini answer
generation.

**Reason:** The baseline should be credible rather than intentionally broken.
It should still expose real failure modes: retrieval misses, OCR/table misses,
grounding failures, and temporal conflicts.

### 10. Use a reranker only in the fixed pipeline

**Decision:** The baseline has no reranker. The fixed pipeline uses
`gemini-3-flash-preview` as an evidence selector/reranker after broad hybrid
retrieval.

**Reason:** The reranker is part of the improvement being evaluated. Keeping it
out of the baseline makes the comparison clearer. In the fixed pipeline,
hybrid retrieval is responsible for recall, while Gemini evidence selection
handles judgment over the candidate set.

### 11. Target Problem A's implemented fix at citation grounding/refusal

**Decision:** The implemented Problem A fix should add claim-level citation
verification, answer repair, and conservative refusal thresholds.

**Reason:** Citation integrity is the top evaluation criterion in the brief.
Extraction and temporal conflict fixes matter, but unsupported claims are the
highest-risk behavior because they can look authoritative while being wrong.

### 12. Use the provided 15 queries as the eval backbone

**Decision:** Run all 15 `baseline_queries.json` questions for Problem A and
reuse them for the production-style eval harness, with at least 10 labeled
golden cases.

**Reason:** Reusing the provided queries keeps the submission coherent. The
same evidence can support failure analysis, before/after comparisons, and CI
regression checks.

### 13. Make deterministic checks hard CI gates

**Decision:** CI should hard-fail on deterministic issues: invalid citations,
missing gold evidence in top-k, schema errors, and citation-support regressions.
LLM-as-judge and human quality scores should warn, not block.

**Reason:** LLM judgment is useful but noisy. Deterministic citation and
retrieval checks are reproducible enough to protect PRs that touch retrieval or
prompts.

### 14. Support startup ingestion and explicit re-ingestion

**Decision:** On startup, ingest only when the corpus/version is missing or
changed. Also expose `/ingest?force=true` for manual rebuilds.

**Reason:** `docker compose up` should be turnkey, but Gemini calls should not
repeat on every restart. A corpus hash manifest gives repeatability and cost
control.

### 15. Commit writeups and small eval fixtures, not generated corpus artifacts

**Decision:** Commit markdown analyses, golden eval JSON, and before/after
summaries. Keep full extracted chunks, caches, and large run logs generated or
gitignored.

**Reason:** Reviewers need to inspect reasoning and reproducible summaries, not
large generated intermediate data. This keeps the repo reviewable.

### 16. Keep structured facts scoped to IN-09 first

**Decision:** Implement structured extraction first for the three IN-09
corrigenda: document identity, tender/package ID, corrigendum number/date,
last-date-for-addendum values, and source chunk citations.

**Reason:** Broad entity/relation extraction would be noisy and expensive. The
IN-09 conflict is the concrete judged failure mode. Keeping the schema
extensible is useful, but the implementation should not spend time extracting
facts across all 20 documents until the core service and Problem A are working.

### 17. Use conservative refusal

**Decision:** If no retrieved evidence passes support checks, the system should
refuse rather than answer with caveats.

**Reason:** The brief explicitly says not to make up answers. In this domain,
an unsupported answer can create more harm than a refusal because construction
and tender decisions depend on traceable evidence.

### 18. Pin Gemini models explicitly

**Decision:** Use `gemini-3-flash-preview` as the default generation, extraction,
reranking, and judging model. Use `gemini-embedding-2` with
`output_dimensionality=768` for chunk and query embeddings.

**Reason:** Pinning model names prevents implementation drift. A 768-dimension
embedding keeps pgvector storage and retrieval cheap while staying compatible
with Gemini's supported output dimensions. Model names remain configurable so a
stronger generator or verifier can be substituted if evals show Flash is not
reliable enough.

### 19. Use `uv` for Python and Docker-only Postgres

**Decision:** Manage the Python environment with `uv`. Run Postgres only via
Docker Compose using a Postgres 16 image with pgvector enabled.

**Reason:** `uv` gives fast, reproducible dependency setup for the local app.
Docker-only Postgres keeps reviewer setup predictable and avoids drift from
locally installed database versions or missing pgvector extensions.

## Rejected or Deferred Alternatives

### Full knowledge-graph-first pipeline

Deferred because it would shift too much effort into schema design and
extraction quality before proving the basic cited-answer service.

### General fact extraction across all documents

Deferred because Q1 only needs structured conflict handling for IN-09 to
demonstrate Problem B. Broad typed extraction can be revisited after the core
RAG and eval path work.

### Gemini-first ingestion for every page

Rejected as the default because it would be slower, more expensive, and less
deterministic than local extraction plus targeted fallback.

### Local-only extraction

Rejected because scanned DGMS PDFs and table-heavy BOQ documents are likely to
produce important extraction misses.

### Raw LLM token streaming

Rejected because it can stream unsupported claims before citation verification
has a chance to catch them.

### Paragraph-level citations

Rejected because they are easier to read but weaker than the brief's
claim-level citation requirement.

### Pro-everywhere model tiering

Deferred because the current implementation should fit the available Gemini
credits and prioritize a working, reproducible system. The model config should
allow upgrading selected steps later.

## Open to Revisit

- Upgrade final answer generation or citation verification from Flash to a
  stronger Gemini model if evals show Flash cannot reliably follow the
  citation contract.
- Expand the conflict sidecar beyond IN-09 only if the 15-query benchmark shows
  structured facts materially outperform evidence-first RAG.
- Add a local cross-encoder reranker if Gemini evidence selection becomes too
  slow, too expensive, or too variable for regression testing.
