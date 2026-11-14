"""M2 theo BRD (macro chỉ nhãn có support ≥ 5) trên bộ chấm của Data Lead, và M9 (X-28)."""

import pytest

from ai_pipeline.evaluation.metrics.explanation_quality import (
    ExplanationRating,
    evaluate_explanation_quality,
)
from ai_pipeline.evaluation.metrics.risk_classification import (
    MIN_SUPPORT,
    RiskRecord,
    evaluate_risk_classification,
)


def _r(clause, label, doc="D1"):
    return RiskRecord(clause, "EMPLOYEE", label, "UNFAVORABLE", document_id=doc)


def test_m2_brd_macro_uses_only_labels_with_min_support():
    gold = [_r(f"cl_{i:04}", "PROBATION") for i in range(MIN_SUPPORT)] + [_r("cl_0099", "BONUS_BENEFITS")]
    pred = [_r(f"cl_{i:04}", "PROBATION") for i in range(MIN_SUPPORT - 1)] + [_r("cl_0099", "REST_AND_LEAVE")]
    result = evaluate_risk_classification(gold, pred)
    assert result["labels_min_support"] == ["PROBATION"]
    assert result["macro_f1_min_support"] == pytest.approx(2 * 4 / (2 * 4 + 0 + 1))
    assert result["macro_f1_present_labels"] < result["macro_f1_min_support"]


def test_m2_brd_macro_none_without_enough_support():
    result = evaluate_risk_classification([_r("cl_0001", "PROBATION")], [_r("cl_0001", "PROBATION")])
    assert result["macro_f1_min_support"] is None and result["labels_min_support"] == []


def test_m9_rates_and_validation():
    rows = [ExplanationRating("o1", "D1", "CORRECT"), ExplanationRating("o2", "D1", "PARTIAL"),
            ExplanationRating("o3", "D2", "WRONG"), ExplanationRating("o4", "D2", "CORRECT")]
    r = evaluate_explanation_quality(rows)
    assert (r["correct_rate"], r["partial_rate"]) == (0.5, 0.25)
    with pytest.raises(ValueError):
        evaluate_explanation_quality([ExplanationRating("o1", "D1", "MAYBE")])
    with pytest.raises(ValueError):
        evaluate_explanation_quality([rows[0], rows[0]])
