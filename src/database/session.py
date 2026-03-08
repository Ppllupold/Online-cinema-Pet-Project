from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy import create_engine

from src.config.settings import get_settings

settings = get_settings()

async_postgresql_engine: AsyncEngine = create_async_engine(
    url=settings.async_db_url,
    echo=settings.DB_ECHO,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_postgresql_engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)
sync_postgresql_engine = create_engine(settings.sync_db_url, echo=False)
