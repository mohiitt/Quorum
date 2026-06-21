"""Application configuration loaded from environment variables / .env file."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    # --- Redis ---
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # --- Anthropic ---
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-haiku-4-5-20251001", alias="ANTHROPIC_MODEL")

    # --- Sentry ---
    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")

    # --- Arize ---
    arize_api_key: str = Field(default="", alias="ARIZE_API_KEY")
    arize_space_key: str = Field(default="", alias="ARIZE_SPACE_KEY")
    arize_model_id: str = Field(default="quorum-validators", alias="ARIZE_MODEL_ID")

    # --- Browserbase ---
    browserbase_api_key: str = Field(default="", alias="BROWSERBASE_API_KEY")
    browserbase_project_id: str = Field(default="", alias="BROWSERBASE_PROJECT_ID")

    # --- External data APIs ---
    openweather_api_key: str = Field(default="", alias="OPENWEATHER_API_KEY")
    pubmed_api_key: str = Field(default="", alias="PUBMED_API_KEY")

    # --- Consensus thresholds ---
    consensus_accept_threshold: float = Field(
        default=0.70, alias="CONSENSUS_ACCEPT_THRESHOLD", ge=0.0, le=1.0
    )
    consensus_reject_threshold: float = Field(
        default=0.30, alias="CONSENSUS_REJECT_THRESHOLD", ge=0.0, le=1.0
    )

    # --- API server ---
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton."""
    return Settings()


def reset_settings() -> None:
    """Clear the cached Settings singleton (useful in tests that mutate env vars)."""
    get_settings.cache_clear()
