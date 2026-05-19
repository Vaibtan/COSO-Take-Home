from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from app.config import Settings, get_settings


class Database:
    def __init__(self, settings: Settings) -> None:
        self._engine: AsyncEngine = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        async with self._engine.begin() as connection:
            yield connection

    async def health_check(self) -> bool:
        async with self._engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            return bool(result.scalar_one() == 1)

    async def dispose(self) -> None:
        await self._engine.dispose()


def create_database(settings: Settings | None = None) -> Database:
    return Database(settings or get_settings())
