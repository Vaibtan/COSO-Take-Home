from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncConnection

from app.config import Settings
from app.llm import GeminiClient
from app.retrieval.repository import ChunkRepository, merge_evidence
from app.schemas import EvidenceChunk, QueryMode


class RetrievalService:
    def __init__(
        self,
        settings: Settings,
        llm: GeminiClient,
        repository: ChunkRepository | None = None,
    ) -> None:
        self._settings = settings
        self._llm = llm
        self._repository = repository or ChunkRepository()

    async def retrieve(
        self, connection: AsyncConnection, question: str, mode: QueryMode
    ) -> list[EvidenceChunk]:
        query_embedding = await self._llm.embed_query(question)
        if mode is QueryMode.baseline:
            return await self._repository.vector_search(
                connection, query_embedding, limit=self._settings.baseline_top_k
            )
        vector = await self._repository.vector_search(
            connection, query_embedding, limit=self._settings.fixed_vector_top_k
        )
        lexical = await self._repository.lexical_search(
            connection, question, limit=self._settings.fixed_lexical_top_k
        )
        return merge_evidence(vector, lexical, limit=self._settings.fixed_vector_top_k)
