"""Synthetic policy checks; no restricted contract text enters these tests."""

import pytest

from scripts.run_m2_dev_evaluation import gold_from_injections


def _case(label="EMPLOYEE_OBLIGATIONS_DISCIPLINE", *, start=12, end=18,
          decision="VERIFIED"):
    return {"clause_id": "d2seg_0001", "risk_label": label,
            "insertion_span": {"start_char": start, "end_char": end},
            "verification": [{"decision": decision}]}


def test_approved_d2_policy_expands_verified_case_to_both_roles():
    spans = [{"gold_clause_ref": "d2seg_0001", "start_char": 10, "end_char": 30}]
    records = gold_from_injections([_case()], spans, "D2:HDLD001")
    assert {(r.role, r.risk_label, r.basis_type) for r in records} == {
        ("EMPLOYEE", "DISCIPLINE_OBLIGATION", "LEGAL_VIOLATION"),
        ("EMPLOYER", "DISCIPLINE_OBLIGATION", "LEGAL_VIOLATION"),
    }
    assert all((r.start_char, r.end_char) == (10, 30) for r in records)


def test_insertion_resolves_to_clause_with_eighty_percent_containment():
    spans = [{"gold_clause_ref": "d2seg_0001", "start_char": 10, "end_char": 30}]
    records = gold_from_injections([_case(start=22, end=32)], spans, "D2:HDLD001")
    assert len(records) == 2


def test_duplicate_injections_in_one_gold_clause_count_one_label_per_role():
    spans = [{"gold_clause_ref": "d2seg_0001", "start_char": 10, "end_char": 30}]
    records = gold_from_injections([_case(), _case(start=18, end=25)], spans,
                                   "D2:HDLD001")
    assert len(records) == 2


@pytest.mark.parametrize("case", [
    _case(decision="PENDING"),
    _case(start=5),
    _case(label="UNILATERAL_CHANGE"),
])
def test_unapproved_or_inconsistent_d2_gold_is_rejected(case):
    spans = [{"gold_clause_ref": "d2seg_0001", "start_char": 10, "end_char": 30}]
    with pytest.raises(ValueError):
        gold_from_injections([case], spans, "D2:HDLD001")
