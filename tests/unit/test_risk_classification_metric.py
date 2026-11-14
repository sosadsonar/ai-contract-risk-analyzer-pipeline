"""M2 / M2b / M9 (X-28, N3)."""

import pytest

from ai_pipeline.evaluation.metrics.risk_classification import (
    ExplanationRating,
    RiskTriple,
    evaluate_basis_type,
    evaluate_explanation_quality,
    evaluate_risk_classification,
)


def _t(doc, clause, label, basis="UNFAVORABLE", role="EMPLOYEE"):
    return RiskTriple(doc, clause, role, label, basis)


def test_m2_macro_uses_only_labels_with_min_support():
    gold = [_t("D1", f"c{i}", "PROBATION") for i in range(5)] + [_t("D1", "c9", "BONUS_BENEFITS")]
    pred = [_t("D1", f"c{i}", "PROBATION") for i in range(4)] + [_t("D1", "c9", "REST_AND_LEAVE")]
    r = evaluate_risk_classification(gold, pred)
    assert r["macro_labels"] == ["PROBATION"]
    assert r["labels_below_min_support"] == ["BONUS_BENEFITS"]
    assert r["macro_f1"] == pytest.approx(2 * 1 * 0.8 / 1.8)
    assert r["per_class"]["REST_AND_LEAVE"]["fp"] == 1


def test_m2_role_is_part_of_the_triple():
    gold = [_t("D1", "c1", "PROBATION", role="EMPLOYEE")]
    pred = [_t("D1", "c1", "PROBATION", role="EMPLOYER")]
    r = evaluate_risk_classification(gold, pred, min_support=1)
    assert r["macro_f1"] == 0.0


def test_m2_rejects_duplicates():
    with pytest.raises(ValueError):
        evaluate_risk_classification([_t("D1", "c1", "PROBATION")] * 2, [])


def test_m2b_only_on_matched_triples():
    gold = [_t("D1", "c1", "PROBATION", "LEGAL_VIOLATION"), _t("D2", "c2", "PROBATION", "AMBIGUOUS")]
    pred = [_t("D1", "c1", "PROBATION", "LEGAL_VIOLATION"), _t("D2", "c2", "PROBATION", "UNFAVORABLE"),
            _t("D2", "c3", "PROBATION", "UNFAVORABLE")]
    r = evaluate_basis_type(gold, pred)
    assert (r["matched"], r["correct"], r["accuracy"]) == (2, 1, 0.5)
    assert r["confusion"] == {"AMBIGUOUS->UNFAVORABLE": 1, "LEGAL_VIOLATION->LEGAL_VIOLATION": 1}


def test_m9_rates_and_validation():
    rows = [ExplanationRating("o1", "D1", "CORRECT"), ExplanationRating("o2", "D1", "PARTIAL"),
            ExplanationRating("o3", "D2", "WRONG"), ExplanationRating("o4", "D2", "CORRECT")]
    r = evaluate_explanation_quality(rows)
    assert (r["correct_rate"], r["partial_rate"]) == (0.5, 0.25)
    with pytest.raises(ValueError):
        evaluate_explanation_quality([ExplanationRating("o1", "D1", "MAYBE")])
    with pytest.raises(ValueError):
        evaluate_explanation_quality([rows[0], rows[0]])
