from __future__ import annotations

from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as db:
        yield db


async def get_db_transactional() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as db:
        async with db.begin():
            yield db
