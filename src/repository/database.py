from __future__ import annotations

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DEFAULT_DATABASE_URL = "postgresql+asyncpg://todo_user:todo_pass@localhost:5432/todo"


def _normalize_database_url(url: str) -> str:
    if "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    if "+" in scheme:
        return url
    if scheme == "postgresql":
        return f"postgresql+asyncpg://{rest}"
    if scheme == "postgres":
        return f"postgresql+asyncpg://{rest}"
    return url


def get_database_url() -> str:
    raw = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    return _normalize_database_url(raw)


engine = create_async_engine(get_database_url(), echo=False, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def dispose_engine() -> None:
    await engine.dispose()
