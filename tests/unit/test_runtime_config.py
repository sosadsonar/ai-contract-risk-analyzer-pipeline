"""Deployment guards keep sample routes out of demo/eval."""

import os
import subprocess
import sys

import pytest

from app.core.config import Settings, load_settings, validate_for_env


def test_dev_optional_quota_and_env_reload(monkeypatch):
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.delenv("DAILY_LLM_CALL_QUOTA", raising=False)
    assert load_settings().DAILY_LLM_CALL_QUOTA is None
    monkeypatch.setenv("DAILY_LLM_CALL_QUOTA", "37")
    assert load_settings().DAILY_LLM_CALL_QUOTA == 37


@pytest.mark.parametrize("override", [
    {}, {"GEMINI_API_KEY": "key", "GEMINI_MODEL_ID": "model"},
    {"WEB_CONCURRENCY": 2}, {"DEV_LLM_PROVIDER": "local"},
    {"CLAUSE_GRAPH_ENABLED": False},
])
def test_demo_rejects_missing_or_unsafe_configuration(override):
    complete = dict(APP_ENV="demo", GEMINI_API_KEY="key", GEMINI_MODEL_ID="model",
                    DAILY_LLM_CALL_QUOTA=30, SESSION_CALL_RESERVE=4)
    if not override or "GEMINI_API_KEY" in override:
        complete.pop("DAILY_LLM_CALL_QUOTA")
        complete.pop("SESSION_CALL_RESERVE")
    complete.update(override)
    with pytest.raises(ValueError):
        validate_for_env(Settings(**complete))


def test_demo_cannot_expose_mock_even_with_valid_config():
    env = os.environ.copy()
    env.update(APP_ENV="demo", GEMINI_API_KEY="test", GEMINI_MODEL_ID="test",
               DAILY_LLM_CALL_QUOTA="30", SESSION_CALL_RESERVE="4")
    result = subprocess.run([sys.executable, "-c",
                             "import sys; sys.path.insert(0, 'backend'); from app.main import app"],
                            env=env, text=True, capture_output=True)
    assert result.returncode != 0
    assert "Pipeline C-05/C-06" in result.stderr
