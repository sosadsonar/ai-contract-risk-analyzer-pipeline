from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    database_url: str
    pdf_max_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    pdf_max_pages: int = Field(default=100, gt=0)
    pdf_max_text_chars: int = Field(default=300_000, gt=0)
    pdf_parse_timeout_seconds: float = Field(default=10, gt=0)
    pdf_worker_memory_mb: int = Field(default=512, ge=128)
    pdf_max_concurrent_uploads: int = Field(default=2, ge=1, le=16)
    pdf_uploads_per_minute: int = Field(default=30, gt=0)
    pdf_body_timeout_seconds: float = Field(default=30, gt=0)
    pdf_max_stored_contracts: int = Field(default=1000, gt=0)
    pdf_max_stored_text_chars: int = Field(default=10_000_000, gt=0)

    model_config = SettingsConfigDict(
        env_file=".env"
    )


settings = Settings()
