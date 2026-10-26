"""Runtime configuration for the N4 development API and future pipeline."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_ENV: Literal["dev", "demo", "eval"] = "dev"
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL_ID: str | None = None
    DEV_LLM_PROVIDER: Literal["gemini", "local"] = "gemini"
    LLM_TIMEOUT_SECONDS: int = Field(default=30, gt=0)
    LLM_AUTO_RETRY: int = Field(default=1, ge=0, le=1)
    CLAUSE_BATCH_SIZE: int = Field(default=20, gt=0)
    RISK_BATCH_SIZE: int = Field(default=6, gt=0)
    LLM_PARALLELISM: int = Field(default=2, gt=0)
    MAX_PDF_PAGES: int = Field(default=30, gt=0)
    MAX_UPLOAD_MB: int = Field(default=10, gt=0)
    MAX_DOCX_CHARS: int = Field(default=100000, gt=0)
    MAX_CLAUSES: int = Field(default=150, gt=0)
    SESSION_TTL_MINUTES: int = Field(default=60, gt=0)
    EXPIRED_TOMBSTONE_HOURS: int = Field(default=24, gt=0)
    DAILY_LLM_CALL_QUOTA: int | None = Field(default=None, gt=0)
    SESSION_CALL_RESERVE: int | None = Field(default=None, gt=0)
    RATE_LIMIT_UPLOADS: int = Field(default=5, gt=0)
    OPS_DB_PATH: str = "./runtime/ops_metadata.sqlite3"
    RATE_LIMIT_HMAC_SALT: str | None = None
    RATE_LIMIT_WINDOW_SECONDS: int = Field(default=600, gt=0)
    DATA_GRAPH_ENABLED: bool = True
    CLAUSE_GRAPH_ENABLED: bool = True
    RETRIEVAL_SEED_K: int = Field(default=3, gt=0)
    RETRIEVAL_FINAL_K: int = Field(default=8, gt=0)
    GRAPH_MAX_NEIGHBORS_PER_SEED: int = Field(default=4, gt=0)
    GRAPH_MAX_CHILDREN_PER_SEED: int = Field(default=2, gt=0)
    CLAUSE_GRAPH_MAX_RELATED: int = Field(default=3, gt=0)
    CLAUSE_GRAPH_MAX_CONTEXT_CHARS: int = Field(default=6000, gt=0)
    SCOPE_TITLE_SCAN_CHARS: int = Field(default=1000, gt=0)
    TEMPERATURE: float = Field(default=0.0, ge=0)
    WEB_CONCURRENCY: int = Field(default=1, ge=1)


def load_settings() -> Settings:
    """Load current environment; never cache credentials at import time."""
    return Settings()


def validate_for_env(s: Settings) -> None:
    """Reject invalid deployment configuration before serving requests."""
    if s.APP_ENV != "dev":
        if s.DEV_LLM_PROVIDER == "local":
            raise ValueError("Local provider is only available in dev")
        if s.WEB_CONCURRENCY != 1:
            raise ValueError("Demo/eval require exactly one worker")
        if not all((s.GEMINI_API_KEY, s.GEMINI_MODEL_ID,
                    s.DAILY_LLM_CALL_QUOTA, s.SESSION_CALL_RESERVE,
                    s.RATE_LIMIT_HMAC_SALT)):
            raise ValueError("Demo/eval require Gemini key, model, daily quota, reserve and rate salt")
        if s.APP_ENV == "demo" and not s.CLAUSE_GRAPH_ENABLED:
            raise ValueError("Demo requires CLAUSE_GRAPH_ENABLED=true")
