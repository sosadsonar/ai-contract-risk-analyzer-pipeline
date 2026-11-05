"""Eval calls use a separate cost ledger; no product usage or contract text persists."""

import asyncio
import csv

import pytest
from app.ai.provider import LLMResponse, ProviderFailure, call_with_retry
from app.ops.metadata_db import MetadataDB
from app.ops.quota import EvalCostLedger


def test_eval_retries_are_recorded_before_call_and_never_charge_product_quota(tmp_path):
    db = MetadataDB(str(tmp_path / "ops.sqlite3"))
    path = tmp_path / "eval_cost_ledger.csv"
    ledger = EvalCostLedger(path, app_env="eval")
    secret = "Hợp đồng riêng 0912345678"

    class Provider:
        attempts = 0

        async def generate_structured(self, **request):
            self.attempts += 1
            assert secret in request["messages"][0]["content"]
            if self.attempts == 1:
                raise ProviderFailure("http", status=429)
            return LLMResponse({"ok": True}, "m", 110, 25, 0.03)

    async def no_sleep(_):
        return None

    provider = Provider()
    asyncio.run(call_with_retry(provider, ledger, model_id="m",
                                messages=[{"role": "user", "content": secret}],
                                response_schema={}, timeout_s=30, sleep=no_sleep))
    assert ledger.summary() == {"calls": 2, "completed": 2, "input_tokens": 110,
                                "output_tokens": 25, "estimated_cost": 0.03, "errors": 1}
    assert db.usage("2026-11-02")["calls"] == 0
    assert secret not in path.read_text(encoding="utf-8")
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert [row["event"] for row in rows] == ["started", "finished", "started", "finished"]
    assert rows[0]["request_id"] == rows[1]["request_id"]
    assert rows[2]["request_id"] == rows[3]["request_id"] != rows[0]["request_id"]
    db.close()


def test_eval_concurrent_calls_have_separate_request_ids(tmp_path):
    path = tmp_path / "eval_cost_ledger.csv"
    ledger = EvalCostLedger(path, app_env="eval")
    both_started = asyncio.Event()

    class Provider:
        attempts = 0

        async def generate_structured(self, **_):
            self.attempts += 1
            if self.attempts == 2:
                both_started.set()
            await both_started.wait()
            return LLMResponse({"ok": True}, "m", 3, 1, 0.1)

    async def one(provider):
        await call_with_retry(provider, ledger, model_id="m", messages=[], response_schema={}, timeout_s=1)

    async def run():
        provider = Provider()
        await asyncio.gather(one(provider), one(provider))

    asyncio.run(run())
    assert ledger.summary() == {"calls": 2, "completed": 2, "input_tokens": 6,
                                "output_tokens": 2, "estimated_cost": 0.2, "errors": 0}
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    started = {row["request_id"] for row in rows if row["event"] == "started"}
    finished = {row["request_id"] for row in rows if row["event"] == "finished"}
    assert len(started) == 2 and started == finished


def test_eval_ledger_rejects_wrong_environment_and_keeps_unfinished_attempt(tmp_path):
    path = tmp_path / "eval_cost_ledger.csv"
    with pytest.raises(ValueError, match="only available in eval"):
        EvalCostLedger(path, app_env="demo")
    assert not path.exists()
    ledger = EvalCostLedger(path, app_env="eval")
    ledger.before_call()
    assert ledger.summary()["calls"] == 1 and ledger.summary()["completed"] == 0
    ledger.after_call(0, 0, 0.0, error_code="invalid_json")
    assert ledger.summary()["errors"] == 1
