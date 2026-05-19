"""initial q1 schema

Revision ID: 0001_initial_q1_schema
Revises:
Create Date: 2026-05-19
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0001_initial_q1_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute(
        """
        CREATE TABLE corpus_documents (
            id BIGSERIAL PRIMARY KEY,
            filename TEXT NOT NULL UNIQUE,
            path TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            ingestion_version TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            page_count INTEGER NOT NULL DEFAULT 0,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE document_pages (
            id BIGSERIAL PRIMARY KEY,
            document_id BIGINT NOT NULL REFERENCES corpus_documents(id) ON DELETE CASCADE,
            page_number INTEGER NOT NULL,
            text TEXT NOT NULL,
            extraction_method TEXT NOT NULL,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE(document_id, page_number)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE chunks (
            id BIGSERIAL PRIMARY KEY,
            stable_id TEXT NOT NULL UNIQUE,
            document_id BIGINT NOT NULL REFERENCES corpus_documents(id) ON DELETE CASCADE,
            page_id BIGINT NOT NULL REFERENCES document_pages(id) ON DELETE CASCADE,
            filename TEXT NOT NULL,
            page_number INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            token_estimate INTEGER NOT NULL,
            embedding vector(768),
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            search_vector tsvector GENERATED ALWAYS AS (
                to_tsvector('english', coalesce(text, ''))
            ) STORED,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_chunks_document_id ON chunks(document_id)")
    op.execute("CREATE INDEX ix_chunks_page_id ON chunks(page_id)")
    op.execute("CREATE INDEX ix_chunks_search_vector ON chunks USING GIN(search_vector)")
    op.execute("CREATE INDEX ix_chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops)")

    op.execute(
        """
        CREATE TABLE conflict_facts (
            id BIGSERIAL PRIMARY KEY,
            tender_id TEXT NOT NULL,
            field_name TEXT NOT NULL,
            field_value TEXT NOT NULL,
            normalized_value TEXT,
            corrigendum_number INTEGER,
            corrigendum_date DATE,
            document_id BIGINT NOT NULL REFERENCES corpus_documents(id) ON DELETE CASCADE,
            chunk_id BIGINT NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
            confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_conflict_facts_lookup ON conflict_facts(tender_id, field_name)")

    op.execute(
        """
        CREATE TABLE eval_runs (
            id BIGSERIAL PRIMARY KEY,
            query_id TEXT,
            question TEXT NOT NULL,
            mode TEXT NOT NULL,
            answer TEXT,
            refusal_reason TEXT,
            evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
            metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS eval_runs")
    op.execute("DROP TABLE IF EXISTS conflict_facts")
    op.execute("DROP TABLE IF EXISTS chunks")
    op.execute("DROP TABLE IF EXISTS document_pages")
    op.execute("DROP TABLE IF EXISTS corpus_documents")
