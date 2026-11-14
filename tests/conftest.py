"""Fixture dùng chung cho test."""
import pytest


@pytest.fixture
def sample_mode(monkeypatch):
    """Ép API về chế độ dev sample (trả fixture, không phân tích file upload), bất kể .env của máy.

    Chế độ do `app.main.pipeline_enabled(settings)` quyết định; `lifespan` đọc `settings` global lúc khởi
    động, nên fixture này phải được yêu cầu TRƯỚC khi tạo `TestClient(app)`. Không autouse: test cần
    pipeline thật (test_pipeline_http, test_pipeline_e2e) không được dùng fixture này.
    """
    from app import main as app_main  # import muộn: app.main đọc cấu hình ngay khi import

    cfg = app_main.settings.model_copy(update={
        "APP_ENV": "dev", "DEV_LLM_PROVIDER": "gemini", "GEMINI_API_KEY": None, "GEMINI_MODEL_ID": None})
    assert not app_main.pipeline_enabled(cfg)
    monkeypatch.setattr(app_main, "settings", cfg)
    return cfg
