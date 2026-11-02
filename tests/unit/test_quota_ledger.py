"""DailyQuota là CallLedger thật: chặn khi hết quota, đếm usage, tương thích call_with_retry."""

import asyncio
from datetime import datetime, timezone

import pytest
from app.ai.provider import LLMResponse, call_with_retry
from app.domain.errors import AiProviderError, LegalCorpusConflict, PipelineInternalError
from app.ops.metadata_db import MetadataDB
from app.ops.quota import DailyQuota

NOW = datetime(2026, 11, 2, 10, tzinfo=timezone.utc)


def make(tmp_path, quota, reserve=2):
    db = MetadataDB(str(tmp_path / "m.db"))
    return db, DailyQuota(db, quota, reserve)


def test_before_call_blocks_when_exhausted_and_does_not_increment(tmp_path):
    db, q = make(tmp_path, 2)
    q.before_call(NOW)
    q.before_call(NOW)
    with pytest.raises(AiProviderError, match="QUOTA_EXHAUSTED"):
        q.before_call(NOW)
    assert db.usage("2026-11-02")["calls"] == 2


def test_quota_none_only_counts(tmp_path):
    db, q = make(tmp_path, None, None)
    for _ in range(5):
        q.before_call(NOW)
    assert db.usage("2026-11-02")["calls"] == 5


def test_quota_resets_next_day(tmp_path):
    _, q = make(tmp_path, 1)
    q.before_call(NOW)
    q.before_call(datetime(2026, 11, 3, tzinfo=timezone.utc))


def test_admission_reserve_uses_remaining(tmp_path):
    _, q = make(tmp_path, 3, reserve=2)
    assert q.admit_new_session(NOW)
    q.before_call(NOW)
    q.before_call(NOW)
    assert not q.admit_new_session(NOW)


def test_after_call_accumulates_usage_and_errors(tmp_path):
    db, q = make(tmp_path, 10)
    q.after_call(100, 20, 0.5, now=NOW)
    q.after_call(0, 0, 0.0, error_code="timeout", now=NOW)
    u = db.usage("2026-11-02")
    assert (u["input_tokens"], u["output_tokens"], u["estimated_cost"], u["errors"]) == (100, 20, 0.5, 1)


def test_works_as_ledger_in_call_with_retry_and_stops_before_sending(tmp_path):
    db, q = make(tmp_path, 1)

    class P:
        sent = 0

        async def generate_structured(self, **kw):
            P.sent += 1
            return LLMResponse({"ok": 1}, "m", 7, 3, 0.25)

    asyncio.run(call_with_retry(P(), q, model_id="m", messages=[], response_schema={}, timeout_s=1))
    with pytest.raises(AiProviderError):
        asyncio.run(call_with_retry(P(), q, model_id="m", messages=[], response_schema={}, timeout_s=1))
    assert P.sent == 1
    u = db.usage(datetime.now(timezone.utc).date().isoformat())
    assert u["calls"] == 1 and u["input_tokens"] == 7


def test_new_domain_errors_have_stable_codes():
    assert PipelineInternalError("x").code == "INTERNAL_ERROR"
    assert LegalCorpusConflict().code == "LEGAL_CORPUS_CONFLICT"
