from __future__ import annotations

from app.query_service import QueryService
from app.schemas import EvidenceChunk, QueryMode, QueryResult


class FakeRetrieval:
    async def retrieve(
        self, connection: object, question: str, mode: QueryMode
    ) -> list[EvidenceChunk]:
        return [
            EvidenceChunk(
                id=1,
                stable_id="doc.pdf:p1:c0",
                filename="doc.pdf",
                page_number=1,
                text=f"{question} {mode.value}",
            )
        ]


class FakeAnswering:
    async def select_evidence(
        self, question: str, candidates: list[EvidenceChunk], mode: QueryMode
    ) -> list[EvidenceChunk]:
        return candidates

    async def answer(
        self, question: str, evidence: list[EvidenceChunk], mode: QueryMode
    ) -> QueryResult:
        return QueryResult(
            answer=f"{mode.value}: {question}",
            refusal_reason=None,
            evidence=evidence,
        )


async def test_query_service_routes_baseline_without_conflict() -> None:
    service = QueryService(FakeRetrieval(), FakeAnswering())  # type: ignore[arg-type]

    result = await service.run_query(None, "What is the bid validity?", QueryMode.baseline)  # type: ignore[arg-type]

    assert result.answer == "baseline: What is the bid validity?"
    assert result.evidence[0].source == "unknown"
