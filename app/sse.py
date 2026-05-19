from __future__ import annotations

from typing import Any

import orjson

from app.schemas import EvidenceChunk


def sse_payload(event: str, data: dict[str, Any]) -> dict[str, str]:
    return {"event": event, "data": orjson.dumps(data).decode("utf-8")}


def evidence_payload(evidence: list[EvidenceChunk]) -> dict[str, Any]:
    return {"evidence": [chunk.model_dump(mode="json", exclude={"text"}) for chunk in evidence]}
