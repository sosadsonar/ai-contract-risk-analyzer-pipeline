import pytest

from ai_pipeline.evaluation.metrics.risk_classification import (
    RiskRecord,
    evaluate_risk_classification,
    map_dev_candidate_to_risk_labels,
)


def rec(clause, role="EMPLOYEE", label="PROBATION", basis="LEGAL_VIOLATION", span=None):
    return RiskRecord(clause, role, label, basis,
                      start_char=span[0] if span else None,
                      end_char=span[1] if span else None)


def test_exact_match_and_m2b_basis_accuracy():
    result = evaluate_risk_classification([rec("cl_0001")], [rec("cl_0001")])
    assert result["macro_f1_present_labels"] == 1
    assert result["macro_f1_all_21_labels"] == pytest.approx(1 / 21)
    assert result["micro_f1"] == 1
    assert result["gold_label_coverage"] == {"present": 1, "total": 21}
    assert result["basis_type_accuracy"] == 1
    assert result["basis_type_ci95"] is not None


@pytest.mark.parametrize("wrong", [
    rec("cl_0001", role="EMPLOYER"),
    rec("cl_0001", label="DEPOSIT_DOCUMENT_HELD"),
])
def test_wrong_role_or_label_is_fp_and_fn(wrong):
    result = evaluate_risk_classification([rec("cl_0001")], [wrong])
    assert result["micro_counts"] == {"tp": 0, "fp": 1, "fn": 1}
    assert result["per_label"]["PROBATION"]["fn"] == 1
    assert result["basis_type_accuracy"] is None


def test_sparse_gold_reports_present_and_all_label_macros_separately():
    gold = [rec("cl_0001"), rec("cl_0002", label="SOCIAL_INSURANCE")]
    pred = [rec("cl_0001"), rec("cl_0002", label="SOCIAL_INSURANCE")]
    result = evaluate_risk_classification(gold, pred)
    assert result["macro_f1_present_labels"] == 1
    assert result["macro_f1_all_21_labels"] == pytest.approx(2 / 21)
    assert result["full_taxonomy_coverage"] is False


def test_span_alignment_maps_different_clause_ids_before_label_scoring():
    gold = [rec("gold_A", span=(10, 30))]
    pred = [rec("pred_B", span=(12, 32))]
    result = evaluate_risk_classification(gold, pred)
    assert result["alignment_pairs"] == 1
    assert result["micro_counts"] == {"tp": 1, "fp": 0, "fn": 0}


def test_gold_clause_contained_in_long_prediction_aligns_without_insertion_span():
    gold = [rec("gold_clause", span=(100, 200))]
    predicted = [rec("pred_clause", span=(50, 400))]
    result = evaluate_risk_classification(gold, predicted)
    assert result["micro_counts"] == {"tp": 1, "fp": 0, "fn": 0}


def test_containment_alignment_remains_one_to_one():
    gold = [rec("gold_one", span=(100, 200)), rec("gold_two", span=(210, 310))]
    predicted = [rec("pred_big", span=(50, 400))]
    result = evaluate_risk_classification(gold, predicted)
    assert result["micro_counts"] == {"tp": 1, "fp": 0, "fn": 1}


def test_basis_mismatch_only_reduces_m2b():
    result = evaluate_risk_classification(
        [rec("cl_0001")], [rec("cl_0001", basis="AMBIGUOUS")])
    assert result["micro_f1"] == 1
    assert result["basis_type_accuracy"] == 0


def test_legacy_m5_label_bridge_is_explicit():
    assert map_dev_candidate_to_risk_labels((
        ("EMPLOYEE", "EMPLOYEE_OBLIGATIONS_DISCIPLINE"),
        ("EMPLOYER", "DEPOSIT_DOCUMENT_HELD"),
    )) == (("EMPLOYEE", "DISCIPLINE_OBLIGATION"),
           ("EMPLOYER", "DEPOSIT_DOCUMENT_HELD"))
