"""Chọn provider theo cấu hình (TDD §4.1). Demo/eval luôn là Gemini paid."""

from __future__ import annotations

import os

from app.ai.dev_local_client import DevLocalClient
from app.ai.gemini_client import GeminiProductClient
from app.ai.provider import LLMProvider


def make_provider(cfg) -> LLMProvider:
    if cfg.APP_ENV == "dev" and cfg.DEV_LLM_PROVIDER == "local":
        return DevLocalClient(
            app_env=cfg.APP_ENV,
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=cfg.TEMPERATURE,
        )
    return GeminiProductClient(cfg.GEMINI_API_KEY, temperature=cfg.TEMPERATURE)
