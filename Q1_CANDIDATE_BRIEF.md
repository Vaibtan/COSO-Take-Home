# COSO Backend Take-Home — Question 1

**RAG over Messy Construction Documents**

---

## Context

COSO builds AI agents that act as a digital civil engineer and project manager inside multi-billion-dollar infrastructure programmes. Real users ask questions like *"what is the bid validity period on the JNPT tender?"* or *"what HEMM safety features are required for opencast mines?"* — and the agent has to answer with traceable citations against a corpus of real, messy construction documents.

This question is about building the retrieval and answering layer that makes this possible.

## What we provide

A folder of **20 real, publicly available construction documents** (`q1_corpus/`):

- NHAI tender documents and pre-bid query-replies (the literal RFI structure)
- DMRC and MPMRCL tender corrigenda — three of these are on the **same Indore Metro IN-09 tender**, issued at different dates, with conflicting deadline information
- DGMS safety circulars — some are scanned PDFs with no extractable text
- BOQ documents with critical information only in table cells
- Long-form RFPs (one is 257 pages)

The corpus is intentionally messy. Some PDFs are clean text. Some are scanned. Some have critical info trapped in tables. This is what real construction data looks like.

We also provide **`baseline_queries.json`** with 15 queries you'll use in Problem A below.

## Part 1 — Build the service (table stakes)

Build a FastAPI service that:

1. **Ingests** all 20 PDFs into Postgres + pgvector on startup (or via an endpoint)
2. **Exposes `POST /query`** that accepts `{"question": "..."}` and **streams** an Anthropic-generated answer
3. **Every claim** in the answer must cite the source chunk (filename + page number minimum)
4. **Refuses gracefully** when retrieval confidence is below a threshold you choose. Don't make up answers.

### Stack

- Python 3.11+, FastAPI, async/await, Pydantic
- Anthropic SDK for the LLM calls
- Postgres 16 + pgvector
- Any embedding model — local sentence-transformers (free) or paid APIs, your call
- Any framework or no framework

### Deliverable

A GitHub repo (private with access to us is fine) where `docker compose up` brings up Postgres + the API. A README explains what you did and how to run it.

This part is doable with AI tooling in 2-3 hours. We expect it to work.

---

## Part 2 — The three judgment problems

After Part 1 works, complete the following three analyses. The structured deliverable for each lives in your repo — a markdown file per problem, plus any supporting code.

### Problem A — Failure analysis

Run all 15 queries from `baseline_queries.json` against your pipeline. For **each** query:

1. **Capture the result** — what your system returned, including the citations
2. **Categorize the outcome** — retrieval miss, grounding failure, extraction failure, ambiguous ground truth, or working as intended. Define each category yourself in the writeup.
3. **Pick the two failure modes that would matter most to fix in production** — and explain *why those two*. Cost of being wrong, frequency of occurrence, severity of user impact — your reasoning is what we evaluate.
4. **Implement a fix for ONE of them.** Re-run the 15 queries against the fixed pipeline. Show before/after.

This is uncopyable from an LLM because the LLM doesn't know which failure modes matter most to *us*. The "explain why these two" is the core deliverable.

### Problem B — The conflict-over-time problem

Three documents in the corpus are corrigenda on the same Indore Metro IN-09 tender, issued at different dates, with conflicting "last date for issuing addendum" fields.

A user asks: *"What is the last date for issuing addenda on the IN-09 tender?"*

Your baseline pipeline likely returns one of these three answers, picked essentially at random based on chunk ranking. That's a real failure mode in production: the system is confidently wrong.

1. **Demonstrate this failure** on your baseline — show what your unfixed pipeline returns
2. **Propose three different approaches** to handle the conflict (with tradeoffs — cost, latency, user experience, implementation complexity)
3. **Pick one** and implement enough to show it works
4. **Write one paragraph** on what you'd do differently with another week

There is no clean answer here. We're evaluating your defense of the choice, not the choice itself.

### Problem C — Eval design

Design and implement the evaluation harness you would actually use in production at COSO. Not generic. Specifically:

1. **What metric(s) would you use, and why those over the alternatives?** (BLEU, ROUGE, retrieval@k, citation integrity, LLM-as-judge, human rating — what's right for *this* problem?)
2. **How would you build the golden set without burning a domain expert's week?** (Bootstrapping, programmatic generation, weak supervision — your call)
3. **How would you catch regressions in CI on PRs that touch retrieval or prompts?** (What fails the build, what just warns?)
4. **Implement enough of it to demo on 10 queries.** Either reuse the baseline 15 or write your own 10.

An engineer who proposes BLEU score for this problem is a no. An engineer who proposes "retrieval@5 + a small human-rated quality scale + a citation-integrity check that verifies every cited chunk actually contains the claim" is showing the kind of evaluation thinking we're hiring for.

---

## Anthropic API costs

The take-home requires the Anthropic SDK. Total spend is typically under $5 for the whole exercise. New console.anthropic.com accounts get $5 of free credits — sufficient. If that's a blocker for any reason, email us.

## What we care about, in order

1. **Citation integrity** — every claim in your /query response must map to a real chunk that actually contains the claimed information. We will manually verify a sample.
2. **Problem A's failure analysis** — your reasoning about which failures matter is the highest-signal artifact in this submission.
3. **Refusal quality** — does your agent refuse when it should? Does it hallucinate when it can't find an answer?
4. **Problem B's tradeoff defense** — defend your choice, not the alternatives.
5. **Problem C's eval design** — is it real, or is it generic?
6. **Code quality and typing** — typed Pydantic models, async done right, sensible structure.

## What we don't care about

- Fancy chunking — naive is fine if justified
- A frontend — none needed
- Authentication — skip it
- Comprehensive test coverage — one or two tests showing your style is fine
- Sub-second latency — get it working before getting it fast

## The README's required section

The README must include a section titled **"What I used AI tools for, and where I overrode them."**

This is non-optional. We use Claude Code and Cursor heavily ourselves and expect you to. The signal we're looking for is **where your judgment diverged from the AI's first suggestion**, and what reasoning made you override it. A great answer makes specific reference to specific decisions.

A great answer looks like:

> *"Cursor scaffolded the FastAPI app and the initial chunking logic. I rewrote the chunking to be layout-aware after I noticed table rows were splitting mid-row in the BOQ documents. I prompted Claude to draft Problem A's analysis, but I disagreed with its conclusion about which failure mode mattered most — the LLM ranked the OCR errors highest because they're 'fundamental,' but I think the duplicate-corrigendum inconsistency matters more because it produces confidently wrong answers, which destroys user trust. I kept my version."*

A weak answer looks like:

> *"I used Claude to help write the code."*

Or worse, no section at all.

## Working session

If we advance you to the working session (90 minutes, video), we'll ask you to walk through your reasoning on Problem A specifically. Treat the writeup as the thing that matters most.

## Questions

Reply to this email. We'd rather you ask than guess.

---