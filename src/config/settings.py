# src/core/config.py
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyUrl
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
    DATABASE_URL: AnyUrl

    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
