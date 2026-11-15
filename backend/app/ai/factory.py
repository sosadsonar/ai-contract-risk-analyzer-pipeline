"""Chọn provider theo cấu hình (TDD §4.1). Demo/eval luôn là Gemini paid."""

from __future__ import annotations

import os

from app.ai.dev_fake_client import DevFakeClient
from app.ai.dev_local_client import DevLocalClient
from app.ai.gemini_client import GeminiProductClient, Price
from app.ai.provider import LLMProvider


def make_provider(cfg) -> LLMProvider:
    if cfg.APP_ENV == "dev" and cfg.DEV_LLM_PROVIDER == "fake":
        return DevFakeClient(app_env=cfg.APP_ENV)
    if cfg.APP_ENV == "dev" and cfg.DEV_LLM_PROVIDER == "local":
        return DevLocalClient(
            app_env=cfg.APP_ENV,
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=cfg.TEMPERATURE,
        )
    return GeminiProductClient(cfg.GEMINI_API_KEY, temperature=cfg.TEMPERATURE, price=price_from(cfg))


def price_from(cfg) -> Price | None:
    """Bảng giá có nguồn (OI-05 §2.4). Thiếu một trong ba giá trị ⇒ None ⇒ cost ghi 0.0 = chưa biết,
    KHÔNG phải miễn phí; quota call-count không phải trần chi tiêu USD."""
    pin = getattr(cfg, "LLM_PRICE_INPUT_USD_PER_MTOK", None)
    pout = getattr(cfg, "LLM_PRICE_OUTPUT_USD_PER_MTOK", None)
    source = getattr(cfg, "LLM_PRICE_SOURCE", None)
    if pin is None or pout is None or not source:
        return None
    return Price(pin, pout, source)
