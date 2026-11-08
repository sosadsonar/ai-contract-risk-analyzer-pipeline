"""D1 timing must measure real local code without presenting estimates as provider latency."""

from pathlib import Path

import pytest
from app.ops.benchmark_d1 import benchmark_d1, percentile


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


def test_invalid_repeats_are_rejected_before_accessing_private_inputs():
    with pytest.raises(ValueError, match="repeats"):
        benchmark_d1(Path("missing"), repeats=0)
