from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class QueryMode(StrEnum):
    baseline = "baseline"
    fixed = "fixed"


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    mode: QueryMode = QueryMode.fixed


class IngestResponse(BaseModel):
    ingested_documents: int
    skipped_documents: int
    chunks: int


class HealthResponse(BaseModel):
    ok: bool
    database: bool
    ingestion_ready: bool


class EvidenceChunk(BaseModel):
    id: int
    stable_id: str
    filename: str
    page_number: int
    text: str
    score: float | None = None
    source: str = "unknown"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def citation(self) -> str:
        return f"{self.filename} p.{self.page_number}"


class QueryResult(BaseModel):
    answer: str | None
    refusal_reason: str | None
    evidence: list[EvidenceChunk]


class SseEvent(BaseModel):
    event: Literal["status", "retrieved_evidence", "answer_delta", "refusal", "done", "error"]
    data: dict[str, Any]
