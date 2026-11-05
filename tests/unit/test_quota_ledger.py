"""DailyQuota counts real provider calls and admits new sessions only within reserve."""

import asyncio
from datetime import datetime, timezone

import pytest
from app.ai.provider import LLMResponse, ProviderFailure, call_with_retry
from app.domain.errors import LegalCorpusConflict, PipelineInternalError
from app.ops.metadata_db import MetadataDB
from app.ops.quota import DailyQuota

NOW = datetime(2026, 11, 2, 10, tzinfo=timezone.utc)


def make(tmp_path, quota, reserve=2):
    db = MetadataDB(str(tmp_path / "m.db"))
    return db, DailyQuota(db, quota, reserve)


def test_active_session_calls_can_cross_quota_without_admitting_new_upload(tmp_path):
    db, q = make(tmp_path, 1, reserve=1)
    assert q.admit_new_session(NOW)
    q.before_call(NOW)
    q.after_call(1, 1, 0.01)
    q.before_call(NOW)  # retry belongs to the already admitted session
    q.after_call(1, 1, 0.01)
    assert db.usage("2026-11-02")["calls"] == 2
    assert not q.admit_new_session(NOW)


def test_quota_none_only_counts(tmp_path):
    db, q = make(tmp_path, None, None)
    for _ in range(5):
        q.before_call(NOW)
        q.after_call(0, 0, 0.0)
    assert db.usage("2026-11-02")["calls"] == 5


def test_quota_resets_next_day(tmp_path):
    _, q = make(tmp_path, 1)
    q.before_call(NOW)
    q.after_call(0, 0, 0.0)
    q.before_call(datetime(2026, 11, 3, tzinfo=timezone.utc))
    q.after_call(0, 0, 0.0)


def test_admission_reserve_uses_remaining(tmp_path):
    _, q = make(tmp_path, 3, reserve=2)
    assert q.admit_new_session(NOW)
    q.before_call(NOW)
    q.after_call(0, 0, 0.0)
    q.before_call(NOW)
    q.after_call(0, 0, 0.0)
    assert not q.admit_new_session(NOW)


def test_after_call_accumulates_usage_and_errors(tmp_path):
    db, q = make(tmp_path, 10)
    q.before_call(NOW)
    q.after_call(100, 20, 0.5, now=NOW)
    q.before_call(NOW)
    q.after_call(0, 0, 0.0, error_code="timeout", now=NOW)
    u = db.usage("2026-11-02")
    assert (u["input_tokens"], u["output_tokens"], u["estimated_cost"], u["errors"]) == (100, 20, 0.5, 1)


def test_usage_is_attributed_to_request_day_across_midnight(tmp_path):
    db, q = make(tmp_path, 1)
    q.before_call(NOW)
    q.after_call(10, 2, 0.1, now=datetime(2026, 11, 3, tzinfo=timezone.utc))
    assert db.usage("2026-11-02")["input_tokens"] == 10
    assert db.usage("2026-11-03")["input_tokens"] == 0


def test_provider_retry_counts_both_requests_even_after_quota_and_rejects_new_session(tmp_path):
    db, q = make(tmp_path, 1, reserve=1)

    class RetryingProvider:
        attempts = 0

        async def generate_structured(self, **kwargs):
            self.attempts += 1
            if self.attempts == 1:
                raise ProviderFailure("network")
            return LLMResponse({"ok": 1}, "m", 7, 3, 0.25)

    provider = RetryingProvider()
    asyncio.run(call_with_retry(provider, q, model_id="m", messages=[],
                                response_schema={}, timeout_s=1))
    assert provider.attempts == 2
    u = db.usage(datetime.now(timezone.utc).date().isoformat())
    assert u["calls"] == 2 and u["input_tokens"] == 7 and u["errors"] == 1
    assert not q.admit_new_session()


def test_parallel_calls_use_independent_pending_state_and_atomic_counts(tmp_path):
    db, q = make(tmp_path, 1, reserve=1)
    both_started = asyncio.Event()

    class ParallelProvider:
        attempts = 0

        async def generate_structured(self, **kwargs):
            self.attempts += 1
            if self.attempts == 2:
                both_started.set()
            await both_started.wait()
            return LLMResponse({"ok": True}, "m", 5, 2, 0.1)

    async def run():
        provider = ParallelProvider()
        requests = [call_with_retry(provider, q, model_id="m", messages=[],
                                    response_schema={}, timeout_s=1) for _ in range(2)]
        await asyncio.gather(*requests)

    asyncio.run(run())
    usage = db.usage(datetime.now(timezone.utc).date().isoformat())
    assert usage["calls"] == 2 and usage["input_tokens"] == 10
    assert not q.admit_new_session()


def test_schema_invalid_retry_records_both_costs_and_one_error(tmp_path):
    db, q = make(tmp_path, 1, reserve=1)

    class SchemaProvider:
        attempts = 0

        async def generate_structured(self, **kwargs):
            self.attempts += 1
            data = {"ok": True} if self.attempts == 2 else {"unexpected": True}
            return LLMResponse(data, "m", 7, 3, 0.25)

    def validate(data):
        if "ok" not in data:
            raise ValueError("invalid output")
        return data["ok"]

    asyncio.run(call_with_retry(SchemaProvider(), q, model_id="m", messages=[],
                                response_schema={}, timeout_s=1, validate=validate))
    usage = db.usage(datetime.now(timezone.utc).date().isoformat())
    assert usage["calls"] == 2
    assert (usage["input_tokens"], usage["output_tokens"], usage["estimated_cost"], usage["errors"]) == (14, 6, 0.5, 1)


def test_cancelled_provider_attempt_is_counted_without_leaving_a_pending_request(tmp_path):
    db, q = make(tmp_path, 1, reserve=1)

    class CancelledProvider:
        async def generate_structured(self, **kwargs):
            raise asyncio.CancelledError

    async def run():
        with pytest.raises(asyncio.CancelledError):
            await call_with_retry(CancelledProvider(), q, model_id="m", messages=[],
                                  response_schema={}, timeout_s=1)
        q.before_call()
        q.after_call(0, 0, 0.0)

    asyncio.run(run())
    usage = db.usage(datetime.now(timezone.utc).date().isoformat())
    assert usage["calls"] == 2 and usage["errors"] == 1


def test_new_domain_errors_have_stable_codes():
    assert PipelineInternalError("x").code == "INTERNAL_ERROR"
    assert LegalCorpusConflict().code == "LEGAL_CORPUS_CONFLICT"
