"""D1 timing must measure real local code without presenting estimates as provider latency."""

import json
import math
from pathlib import Path

import pytest

from app.core.config import Settings
from app.ops.benchmark_d1 import benchmark_d1, percentile


DATA = Path(__file__).resolve().parents[2] / "ai_pipeline/data"


def test_nearest_rank_with_small_d1_sample_and_repeated_timings():
    assert percentile([40, 10, 30, 20], 0.5) == 20
    assert percentile([40, 10, 30, 20], 0.9) == 40
    assert percentile([10, 20, 30, 40, 50], 0.9) == 50
    with pytest.raises(ValueError, match="nonempty"):
        percentile([], 0.5)

def test_injected_clock_measures_the_executed_operation_not_a_latency_guess():
    from app.ops.benchmark_d1 import _timed

    times = iter((12_000_000, 92_000_000))
    executed = []
    result, duration = _timed(lambda: executed.append("ran") or 7, lambda: next(times))
    assert executed == ["ran"]
    assert result == 7
    assert duration == 80_000_000



def test_real_d1_only_reports_measured_local_stages_and_configured_planned_calls():
    cfg = Settings(_env_file=None, CLAUSE_BATCH_SIZE=10, RISK_BATCH_SIZE=7)
    result = benchmark_d1(DATA, repeats=2, cfg=cfg)
    assert [case["id"] for case in result["cases"]] == ["HDLD001", "HDLD002", "HDLD003", "HDLD004"]
    assert [case["source"] for case in result["cases"]] == ["word_text_snapshot"] * 3 + ["docx"]
    for case in result["cases"]:
        assert case["clauses"] > 0
        assert case["planned_calls"] == math.ceil(case["clauses"] / 10) + math.ceil(case["clauses"] / 7)
        for stats in case["stages"].values():
            assert stats["samples"] == 2
            assert 0 <= stats["p50_ms"] <= stats["p90_ms"]
    assert result["planned_calls_p95"] == max(case["planned_calls"] for case in result["cases"])
    assert all(stage["samples"] == 8 for stage in result["stages"].values())
    assert "llm_1" in result["unmeasured"]
    assert "retrieval_graphs" in result["unmeasured"]
    assert "assembly" in result["unmeasured"]
    assert "masked_text" not in json.dumps(result)


def test_rejects_changed_release_input_before_any_measurement(monkeypatch):
    import app.ops.benchmark_d1 as benchmark

    manifest_path = DATA / "data/releases/v06-rc1/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"]["data/processed/raw_text/HDLD001.txt"] = "0" * 64
    original_read = Path.read_text

    def altered_receipt(path, *args, **kwargs):
        if path == manifest_path:
            return json.dumps(manifest)
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", altered_receipt)
    monkeypatch.setattr(benchmark, "extract", lambda *_a, **_kw: pytest.fail("processed invalid release"))
    with pytest.raises(ValueError, match="hash mismatch: HDLD001"):
        benchmark_d1(DATA, repeats=1)


def test_invalid_repeats_are_rejected_before_accessing_private_inputs():
    with pytest.raises(ValueError, match="repeats"):
        benchmark_d1(Path("missing"), repeats=0)
