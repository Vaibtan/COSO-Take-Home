# COSO Backend Take-Home

This repo contains the COSO take-home work. Q1 is currently implemented as a
FastAPI + Postgres/pgvector cited RAG service over the PDFs in `q1/`.

## Q1 Quick Start

Prerequisites:

- Docker Desktop
- `uv`
- `.env` with `GEMINI_API_KEY=...`

Run the service:

```powershell
uv sync
docker compose up --build
```

Health check:

```powershell
curl.exe http://127.0.0.1:8000/healthz
```

Ingest the corpus:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/ingest?force=false"
```

Query:

```powershell
curl.exe -N -X POST "http://127.0.0.1:8000/query" `
  -H "Content-Type: application/json" `
  -d "{\"question\":\"What is the bid validity period for the JNPT maintenance tender?\",\"mode\":\"fixed\"}"
```

Run the baseline eval set:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/eval/run?mode=baseline"
```

Postgres is intentionally Docker-only for this project. The API container uses
the `db` service from `docker-compose.yml`; local development can connect to the
same Docker database through the exposed `localhost:5432` port.

## Q1 Architecture Notes

- Vector DB: Postgres 16 + pgvector.
- Lexical retrieval: Postgres full-text search.
- Generation/reranking/verifier model: `gemini-3-flash-preview`.
- Embeddings: `gemini-embedding-2`, `output_dimensionality=768`.
- Baseline mode: vector top-k, no reranker, no verifier.
- Fixed mode: hybrid retrieval, Gemini evidence selector/reranker, citation
  verification, conservative refusal, IN-09 conflict sidecar.

See:

- `design-decisions.md`
- `Q1-ARCHITECTURE.md`
- `IMPLEMENTATION-PLAN.md`

## Development Checks

```powershell
uv run ruff check app tests
uv run mypy app
uv run pytest
```

Docker verification:

```powershell
docker compose up -d db
uv run alembic upgrade head
docker compose up -d --build api
curl.exe http://127.0.0.1:8000/healthz
```

## What I used AI tools for, and where I overrode them.

AI tools were used to draft the initial RAG architecture, implementation
checklist, and service scaffold. I overrode the broad KG-first direction by
scoping structured facts to the IN-09 conflict case first, because the judged
deliverable needs a defensible conflict-over-time fix more than a generalized
ontology. I also overrode an outdated embedding recommendation and pinned
`gemini-embedding-2` with 768 dimensions, while using `gemini-3-flash-preview`
because this implementation is intentionally Gemini-based rather than
Anthropic-based.
