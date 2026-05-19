from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.config import Settings
from app.database import Database
from app.ingestion.chunker import PageAwareChunker
from app.ingestion.extractor import PdfExtractor
from app.llm import GeminiClient
from app.utils import sha256_file, vector_literal


@dataclass(frozen=True)
class IngestionStats:
    ingested_documents: int
    skipped_documents: int
    chunks: int


class IngestionPipeline:
    def __init__(
        self,
        settings: Settings,
        llm: GeminiClient,
        extractor: PdfExtractor | None = None,
        chunker: PageAwareChunker | None = None,
    ) -> None:
        self._settings = settings
        self._llm = llm
        self._extractor = extractor or PdfExtractor()
        self._chunker = chunker or PageAwareChunker()

    async def run(self, connection: AsyncConnection, *, force: bool = False) -> IngestionStats:
        corpus_dir = self._settings.corpus_dir
        pdfs = sorted(path for path in corpus_dir.glob("*.pdf") if path.is_file())
        ingested = 0
        skipped = 0
        chunk_count = 0

        for path in pdfs:
            changed = await self._needs_ingestion(connection, path, force=force)
            if not changed:
                skipped += 1
                continue
            chunks = await self._ingest_one(connection, path)
            ingested += 1
            chunk_count += chunks

        return IngestionStats(
            ingested_documents=ingested,
            skipped_documents=skipped,
            chunks=chunk_count,
        )

    async def run_with_commits(self, database: Database, *, force: bool = False) -> IngestionStats:
        corpus_dir = self._settings.corpus_dir
        pdfs = sorted(path for path in corpus_dir.glob("*.pdf") if path.is_file())
        ingested = 0
        skipped = 0
        chunk_count = 0

        for path in pdfs:
            async with database.connect() as connection:
                changed = await self._needs_ingestion(connection, path, force=force)
            if not changed:
                skipped += 1
                continue

            async with database.connect() as connection:
                chunks = await self._ingest_one(connection, path)
            ingested += 1
            chunk_count += chunks

        return IngestionStats(
            ingested_documents=ingested,
            skipped_documents=skipped,
            chunks=chunk_count,
        )

    async def _needs_ingestion(
        self, connection: AsyncConnection, path: Path, *, force: bool
    ) -> bool:
        if force:
            return True
        digest = sha256_file(path)
        row = (
            await connection.execute(
                text(
                    """
                    SELECT sha256, ingestion_version, status
                    FROM corpus_documents
                    WHERE filename = :filename
                    """
                ),
                {"filename": path.name},
            )
        ).mappings().first()
        if row is None:
            return True
        return not (
            row["sha256"] == digest
            and row["ingestion_version"] == self._settings.ingestion_version
            and row["status"] == "ready"
        )

    async def _ingest_one(self, connection: AsyncConnection, path: Path) -> int:
        digest = sha256_file(path)
        await connection.execute(
            text("DELETE FROM corpus_documents WHERE filename = :filename"),
            {"filename": path.name},
        )
        document_id = (
            await connection.execute(
                text(
                    """
                    INSERT INTO corpus_documents(filename, path, sha256, ingestion_version, status)
                    VALUES (:filename, :path, :sha256, :version, 'processing')
                    RETURNING id
                    """
                ),
                {
                    "filename": path.name,
                    "path": str(path),
                    "sha256": digest,
                    "version": self._settings.ingestion_version,
                },
            )
        ).scalar_one()

        pages = await asyncio.to_thread(self._extractor.extract, path)
        chunks = self._chunker.chunk_pages(pages)
        embeddings = await self._llm.embed_documents([chunk.text for chunk in chunks])

        page_id_by_number: dict[int, int] = {}
        for page in pages:
            page_id = (
                await connection.execute(
                    text(
                        """
                        INSERT INTO document_pages(
                            document_id, page_number, text, extraction_method, metadata
                        )
                        VALUES (
                            :document_id, :page_number, :text, :method,
                            CAST(:metadata AS jsonb)
                        )
                        RETURNING id
                        """
                    ),
                    {
                        "document_id": document_id,
                        "page_number": page.page_number,
                        "text": page.text,
                        "method": page.extraction_method,
                        "metadata": json.dumps(page.metadata),
                    },
                )
            ).scalar_one()
            page_id_by_number[page.page_number] = int(page_id)

        for chunk, embedding in zip(chunks, embeddings, strict=True):
            await connection.execute(
                text(
                    """
                    INSERT INTO chunks(
                        stable_id, document_id, page_id, filename, page_number, chunk_index,
                        text, token_estimate, embedding, metadata
                    )
                    VALUES (
                        :stable_id, :document_id, :page_id, :filename, :page_number,
                        :chunk_index, :chunk_text, :token_estimate,
                        CAST(:embedding AS vector), CAST(:metadata AS jsonb)
                    )
                    """
                ),
                {
                    "stable_id": chunk.stable_id,
                    "document_id": document_id,
                    "page_id": page_id_by_number[chunk.page_number],
                    "filename": chunk.filename,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                    "chunk_text": chunk.text,
                    "token_estimate": chunk.token_estimate,
                    "embedding": vector_literal(embedding),
                    "metadata": json.dumps(chunk.metadata),
                },
            )

        await connection.execute(
            text(
                """
                UPDATE corpus_documents
                SET status = 'ready', page_count = :page_count, updated_at = now()
                WHERE id = :document_id
                """
            ),
            {"document_id": document_id, "page_count": len(pages)},
        )
        return len(chunks)
