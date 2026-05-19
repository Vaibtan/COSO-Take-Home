from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncConnection

from app.answering.service import AnsweringService
from app.conflict.in09 import In09ConflictResolver, is_in09_addendum_question
from app.retrieval.service import RetrievalService
from app.schemas import QueryMode, QueryResult


class QueryService:
    def __init__(
        self,
        retrieval: RetrievalService,
        answering: AnsweringService,
        conflict_resolver: In09ConflictResolver | None = None,
    ) -> None:
        self._retrieval = retrieval
        self._answering = answering
        self._conflict_resolver = conflict_resolver or In09ConflictResolver()

    async def run_query(
        self, connection: AsyncConnection, question: str, mode: QueryMode
    ) -> QueryResult:
        if mode is QueryMode.fixed and is_in09_addendum_question(question):
            conflict_answer = await self._conflict_resolver.resolve(connection)
            if conflict_answer is not None:
                return QueryResult(
                    answer=conflict_answer.answer,
                    refusal_reason=None,
                    evidence=conflict_answer.evidence,
                )

        candidates = await self._retrieval.retrieve(connection, question, mode)
        selected = await self._answering.select_evidence(question, candidates, mode)
        return await self._answering.answer(question, selected, mode)
