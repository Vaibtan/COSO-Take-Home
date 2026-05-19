from __future__ import annotations

import asyncio
import json
from typing import Any

from google import genai
from google.genai import types

from app.config import Settings


class GeminiClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        api_key = settings.gemini_api_key.get_secret_value()
        self._client = genai.Client(api_key=api_key) if api_key else genai.Client()

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        batch_size = 32
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            batch_embeddings = await self._embed(batch, task_type="RETRIEVAL_DOCUMENT")
            if len(batch_embeddings) != len(batch):
                for text in batch:
                    embeddings.extend(await self._embed([text], task_type="RETRIEVAL_DOCUMENT"))
            else:
                embeddings.extend(batch_embeddings)
        return embeddings

    async def embed_query(self, text: str) -> list[float]:
        return (await self._embed([text], task_type="RETRIEVAL_QUERY"))[0]

    async def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        if not texts:
            return []
        response = None
        for attempt in range(4):
            try:
                response = await self._client.aio.models.embed_content(
                    model=self._settings.gemini_embedding_model,
                    contents=texts,
                    config=types.EmbedContentConfig(
                        task_type=task_type,
                        output_dimensionality=self._settings.embedding_dimensions,
                    ),
                )
                break
            except Exception:
                if attempt == 3:
                    raise
                await asyncio.sleep(2**attempt)
        if response is None:
            return []
        embeddings = response.embeddings or []
        return [list(embedding.values or []) for embedding in embeddings]

    async def generate_text(self, prompt: str, *, temperature: float = 0.1) -> str:
        response = await self._client.aio.models.generate_content(
            model=self._settings.gemini_generation_model,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=temperature),
        )
        return response.text or ""

    async def generate_json(self, prompt: str) -> dict[str, Any]:
        response = await self._client.aio.models.generate_content(
            model=self._settings.gemini_generation_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
            ),
        )
        raw = response.text or "{}"
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
