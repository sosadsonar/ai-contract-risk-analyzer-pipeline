"""M6 judge calibration (X-08 khung)."""

import pytest

from ai_pipeline.evaluation.metrics.judge_agreement import PairedRating, cohen_kappa, evaluate_judge


def test_kappa_known_value():
    pairs = [PairedRating(str(i), h, j) for i, (h, j) in enumerate(
        [("Y", "Y")] * 20 + [("Y", "N")] * 5 + [("N", "Y")] * 10 + [("N", "N")] * 15)]
    assert cohen_kappa(pairs) == pytest.approx(0.4)
    r = evaluate_judge(pairs)
    assert r["agreement"] == pytest.approx(0.7) and r["passes"] is False


def test_pass_requires_both_thresholds():
    pairs = [PairedRating(str(i), "Y" if i % 2 else "N", "Y" if i % 2 else "N") for i in range(40)]
    assert evaluate_judge(pairs)["passes"] is True
    with pytest.raises(ValueError):
        evaluate_judge([pairs[0], pairs[0]])
