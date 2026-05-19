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
low-text, scanned, or table-critical pages.

**Reason:** The corpus includes clean PDFs, scanned DGMS documents, BOQs, and
corrigenda. Local extraction is cheaper, more deterministic, and preserves page
provenance well. Gemini fallback is used where local extraction is likely to
miss answer-bearing evidence, especially scanned pages and tables.

### 3. Make evidence-first hybrid RAG the main architecture

**Decision:** Build the main answer path around page-aware chunks, lexical plus
vector retrieval, evidence selection, citation verification, and conservative
refusal.

**Reason:** The brief explicitly prioritizes citation integrity over fancy
retrieval. Evidence-first RAG keeps answers grounded in inspectable chunks and
makes failures easier to analyze. It is also a better fit for the required
before/after evaluation than a large, opaque agent workflow.

### 4. Add a KG sidecar, not a full KG-first pipeline

**Decision:** Build a typed fact/event sidecar for benchmarking and conflict
handling, while keeping evidence-first RAG as the production answer path.

**Reason:** A full knowledge-graph-first RAG system would be interesting, but
it is too much implementation risk for the take-home. A sidecar gives us the
benefits that matter here: structured tender metadata, dates, corrigendum
ordering, requirements, quantities, and fact comparison for known conflict
cases.

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

**Decision:** The baseline has no reranker. The fixed pipeline uses Gemini
Flash as an evidence selector/reranker after broad hybrid retrieval.

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

### 16. Keep the KG sidecar scoped to tender/date/fact extraction

**Decision:** Extract document type, tender/package IDs, corrigendum number and
date, deadlines, requirements, quantities, and clause-like facts needed by the
baseline queries.

**Reason:** Broad entity/relation extraction would be noisy and expensive. A
typed fact graph is enough to benchmark KG-style reasoning and solve the IN-09
conflict problem.

### 17. Use conservative refusal

**Decision:** If no retrieved evidence passes support checks, the system should
refuse rather than answer with caveats.

**Reason:** The brief explicitly says not to make up answers. In this domain,
an unsupported answer can create more harm than a refusal because construction
and tender decisions depend on traceable evidence.

### 18. Default to Gemini Flash for model calls

**Decision:** Use Gemini Flash as the default generation, extraction,
reranking, and judging model, with embeddings handled by Gemini embeddings.

**Reason:** Flash keeps the pipeline cheaper and faster while staying within
the Gemini ecosystem. The implementation should leave model names configurable
so a stronger model can be substituted if Flash underperforms on final answer
quality or verification.

## Rejected or Deferred Alternatives

### Full knowledge-graph-first pipeline

Deferred because it would shift too much effort into schema design and
extraction quality before proving the basic cited-answer service.

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
- Expand the KG sidecar beyond tender/date/fact extraction only if the 15-query
  benchmark shows structured facts materially outperform evidence-first RAG.
- Add a local cross-encoder reranker if Gemini evidence selection becomes too
  slow, too expensive, or too variable for regression testing.
