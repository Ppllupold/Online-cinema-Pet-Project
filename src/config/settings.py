# src/core/config.py
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application main settings
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- App ----

    APP_NAME: str = "online-cinema"
    ENV: Literal["local", "test", "prod"] = "local"
    DEBUG: bool = False

    # ---- Database ----

    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str

    DB_ECHO: bool
    DB_POOL_SIZE: int
    DB_MAX_OVERFLOW: int
    DB_POOL_TIMEOUT: int

    @property
    def async_db_url(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def sync_db_url(self) -> str:
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
