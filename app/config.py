from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    gemini_api_key: SecretStr = Field(default=SecretStr(""))
    database_url: str = "postgresql+asyncpg://coso:coso@localhost:5432/coso_q1"
    corpus_dir: Path = Path("q1")

    gemini_generation_model: str = "gemini-3-flash-preview"
    gemini_embedding_model: str = "gemini-embedding-2"
    embedding_dimensions: int = 768

    ingestion_version: str = "q1-v1"
    ingest_on_startup: bool = False

    baseline_top_k: int = 8
    fixed_vector_top_k: int = 20
    fixed_lexical_top_k: int = 20
    fixed_evidence_top_k: int = 8
    refusal_min_evidence: int = 1


@lru_cache
def get_settings() -> Settings:
    return Settings()
