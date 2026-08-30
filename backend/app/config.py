from __future__ import annotations

import json
from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "SignalGraph"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./signalgraph.db"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "development-only-change-me"
    access_token_minutes: int = 60
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:8080"]
    )
    log_level: str = "INFO"
    auto_create_tables: bool = False
    celery_task_always_eager: bool = False
    collector_timeout_seconds: float = 15.0
    raw_response_max_bytes: int = 1_000_000
    urlscan_api_key: str | None = None
    risk_rules: dict[str, int] = Field(
        default_factory=lambda: {
            "malicious_classification": 55,
            "suspicious_classification": 30,
            "high_confidence": 10,
            "many_relationships": 10,
            "vulnerability_entity": 10,
        }
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                decoded = json.loads(stripped)
                if not isinstance(decoded, list):
                    raise ValueError("CORS_ORIGINS JSON value must be a list")
                return decoded
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value

    @field_validator("secret_key")
    @classmethod
    def validate_secret(cls, value: str, info) -> str:
        if info.data.get("environment") == "production" and (
            len(value) < 32 or value == "development-only-change-me"
        ):
            raise ValueError("SECRET_KEY must be at least 32 characters and changed in production")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
