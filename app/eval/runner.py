from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.query_service import QueryService
from app.schemas import QueryMode


@dataclass(frozen=True)
class EvalSummary:
    total: int
    stored: int


class EvalRunner:
    def __init__(self, query_service: QueryService, queries_path: Path) -> None:
        self._query_service = query_service
        self._queries_path = queries_path

    async def run(self, connection: AsyncConnection, mode: QueryMode) -> EvalSummary:
        payload = json.loads(self._queries_path.read_text(encoding="utf-8"))
        queries = payload.get("queries", [])
        stored = 0
        for item in queries:
            query_id = str(item["id"])
            question = str(item["question"])
            result = await self._query_service.run_query(connection, question, mode)
            await connection.execute(
                text(
                    """
                    INSERT INTO eval_runs(
                        query_id, question, mode, answer, refusal_reason, evidence, metrics
                    )
                    VALUES (
                        :query_id, :question, :mode, :answer,
                        :refusal_reason, CAST(:evidence AS jsonb), '{}'::jsonb
                    )
                    """
                ),
                {
                    "query_id": query_id,
                    "question": question,
                    "mode": mode.value,
                    "answer": result.answer,
                    "refusal_reason": result.refusal_reason,
                    "evidence": json.dumps(
                        [chunk.model_dump(mode="json") for chunk in result.evidence]
                    ),
                },
            )
            stored += 1
        return EvalSummary(total=len(queries), stored=stored)
