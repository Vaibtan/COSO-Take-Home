from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()

corpus_documents = Table(
    "corpus_documents",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("filename", Text, nullable=False, unique=True),
    Column("path", Text, nullable=False),
    Column("sha256", Text, nullable=False),
    Column("ingestion_version", Text, nullable=False),
    Column("status", Text, nullable=False, server_default="pending"),
    Column("page_count", Integer, nullable=False, server_default="0"),
    Column("metadata", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

document_pages = Table(
    "document_pages",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("document_id", ForeignKey("corpus_documents.id", ondelete="CASCADE"), nullable=False),
    Column("page_number", Integer, nullable=False),
    Column("text", Text, nullable=False),
    Column("extraction_method", Text, nullable=False),
    Column("metadata", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("document_id", "page_number", name="uq_document_pages_document_page"),
)

chunks = Table(
    "chunks",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("stable_id", Text, nullable=False, unique=True),
    Column("document_id", ForeignKey("corpus_documents.id", ondelete="CASCADE"), nullable=False),
    Column("page_id", ForeignKey("document_pages.id", ondelete="CASCADE"), nullable=False),
    Column("filename", Text, nullable=False),
    Column("page_number", Integer, nullable=False),
    Column("chunk_index", Integer, nullable=False),
    Column("text", Text, nullable=False),
    Column("token_estimate", Integer, nullable=False),
    Column("metadata", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

conflict_facts = Table(
    "conflict_facts",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tender_id", Text, nullable=False),
    Column("field_name", Text, nullable=False),
    Column("field_value", Text, nullable=False),
    Column("normalized_value", Text),
    Column("corrigendum_number", Integer),
    Column("corrigendum_date", Date),
    Column("document_id", ForeignKey("corpus_documents.id", ondelete="CASCADE"), nullable=False),
    Column("chunk_id", ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False),
    Column("confidence", Float, nullable=False, server_default="0"),
    Column("metadata", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

eval_runs = Table(
    "eval_runs",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("query_id", String),
    Column("question", Text, nullable=False),
    Column("mode", String, nullable=False),
    Column("answer", Text),
    Column("refusal_reason", Text),
    Column("evidence", JSONB, nullable=False, server_default="[]"),
    Column("metrics", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
