from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.answering.service import AnsweringService
from app.config import Settings, get_settings
from app.conflict.in09 import In09ConflictResolver
from app.database import Database, create_database
from app.eval.runner import EvalRunner
from app.ingestion.pipeline import IngestionPipeline
from app.llm import GeminiClient
from app.query_service import QueryService
from app.retrieval.repository import ChunkRepository
from app.retrieval.service import RetrievalService
from app.schemas import HealthResponse, IngestResponse, QueryMode, QueryRequest
from app.sse import evidence_payload, sse_payload


class AppState:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.database: Database = create_database(settings)
        self.llm = GeminiClient(settings)
        self.chunk_repository = ChunkRepository()
        self.retrieval = RetrievalService(settings, self.llm, self.chunk_repository)
        self.answering = AnsweringService(settings, self.llm)
        self.conflict_resolver = In09ConflictResolver()
        self.query_service = QueryService(self.retrieval, self.answering, self.conflict_resolver)
        self.ingestion = IngestionPipeline(settings, self.llm)
        self.eval_runner = EvalRunner(
            self.query_service,
            Path(settings.corpus_dir) / "baseline_queries.json",
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    state = AppState(settings)
    app.state.q1 = state
    if settings.ingest_on_startup:
        await state.ingestion.run_with_commits(state.database, force=False)
        async with state.database.connect() as connection:
            await state.conflict_resolver.extract_facts(connection)
    try:
        yield
    finally:
        await state.database.dispose()


app = FastAPI(title="COSO Q1 RAG", version="0.1.0", lifespan=lifespan)


def q1_state() -> AppState:
    state: AppState | None = getattr(app.state, "q1", None)
    if state is None:
        raise HTTPException(status_code=503, detail="Application is not ready")
    return state


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    state = q1_state()
    database_ok = await state.database.health_check()
    async with state.database.connect() as connection:
        chunks = await state.chunk_repository.count_chunks(connection)
    return HealthResponse(ok=database_ok, database=database_ok, ingestion_ready=chunks > 0)


@app.post("/ingest", response_model=IngestResponse)
async def ingest(force: bool = False) -> IngestResponse:
    state = q1_state()
    stats = await state.ingestion.run_with_commits(state.database, force=force)
    async with state.database.connect() as connection:
        await state.conflict_resolver.extract_facts(connection)
    return IngestResponse(
        ingested_documents=stats.ingested_documents,
        skipped_documents=stats.skipped_documents,
        chunks=stats.chunks,
    )


@app.post("/query")
async def query(request: QueryRequest) -> EventSourceResponse:
    state = q1_state()

    async def events() -> AsyncIterator[dict[str, str]]:
        try:
            yield sse_payload("status", {"message": "query_started", "mode": request.mode.value})
            async with state.database.connect() as connection:
                result = await state.query_service.run_query(
                    connection,
                    request.question,
                    request.mode,
                )
            yield sse_payload("retrieved_evidence", evidence_payload(result.evidence))
            if result.refusal_reason is not None:
                yield sse_payload("refusal", {"reason": result.refusal_reason})
            elif result.answer is not None:
                yield sse_payload("answer_delta", {"text": result.answer})
            yield sse_payload("done", {"ok": result.refusal_reason is None})
        except Exception as exc:  # pragma: no cover - keeps SSE clients from hanging
            yield sse_payload("error", {"message": str(exc)})

    return EventSourceResponse(events())


@app.post("/eval/run")
async def run_eval(mode: QueryMode = QueryMode.baseline) -> dict[str, Any]:
    state = q1_state()
    async with state.database.connect() as connection:
        summary = await state.eval_runner.run(connection, mode)
    return {"mode": mode.value, "total": summary.total, "stored": summary.stored}
