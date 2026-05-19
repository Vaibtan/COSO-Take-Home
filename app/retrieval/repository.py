from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.schemas import EvidenceChunk
from app.utils import vector_literal


class ChunkRepository:
    async def count_chunks(self, connection: AsyncConnection) -> int:
        return int((await connection.execute(text("SELECT count(*) FROM chunks"))).scalar_one())

    async def vector_search(
        self, connection: AsyncConnection, embedding: list[float], *, limit: int
    ) -> list[EvidenceChunk]:
        rows = (
            await connection.execute(
                text(
                    """
                    SELECT id, stable_id, filename, page_number, text,
                           1 - (embedding <=> CAST(:embedding AS vector)) AS score,
                           metadata
                    FROM chunks
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> CAST(:embedding AS vector)
                    LIMIT :limit
                    """
                ),
                {"embedding": vector_literal(embedding), "limit": limit},
            )
        ).mappings().all()
        return [
            EvidenceChunk(
                id=int(row["id"]),
                stable_id=str(row["stable_id"]),
                filename=str(row["filename"]),
                page_number=int(row["page_number"]),
                text=str(row["text"]),
                score=float(row["score"]) if row["score"] is not None else None,
                source="vector",
                metadata=dict(row["metadata"] or {}),
            )
            for row in rows
        ]

    async def lexical_search(
        self, connection: AsyncConnection, query: str, *, limit: int
    ) -> list[EvidenceChunk]:
        rows = (
            await connection.execute(
                text(
                    """
                    WITH q AS (SELECT websearch_to_tsquery('english', :query) AS tsq)
                    SELECT c.id, c.stable_id, c.filename, c.page_number, c.text,
                           ts_rank_cd(c.search_vector, q.tsq) AS score,
                           c.metadata
                    FROM chunks c, q
                    WHERE c.search_vector @@ q.tsq
                    ORDER BY score DESC
                    LIMIT :limit
                    """
                ),
                {"query": query, "limit": limit},
            )
        ).mappings().all()
        return [
            EvidenceChunk(
                id=int(row["id"]),
                stable_id=str(row["stable_id"]),
                filename=str(row["filename"]),
                page_number=int(row["page_number"]),
                text=str(row["text"]),
                score=float(row["score"]) if row["score"] is not None else None,
                source="lexical",
                metadata=dict(row["metadata"] or {}),
            )
            for row in rows
        ]


def merge_evidence(*groups: list[EvidenceChunk], limit: int) -> list[EvidenceChunk]:
    merged: dict[int, EvidenceChunk] = {}
    for group in groups:
        for item in group:
            existing = merged.get(item.id)
            if existing is None:
                merged[item.id] = item
                continue
            old_score = existing.score or 0.0
            new_score = item.score or 0.0
            source = (
                existing.source
                if item.source in existing.source
                else f"{existing.source}+{item.source}"
            )
            merged[item.id] = existing.model_copy(
                update={"score": max(old_score, new_score), "source": source}
            )
    return sorted(merged.values(), key=lambda item: item.score or 0.0, reverse=True)[:limit]
