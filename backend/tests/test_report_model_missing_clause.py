"""build_report_model: risk trỏ tới clause không tồn tại phải báo lỗi, không bỏ qua im lặng."""

import pytest
from app.result.report_model import build_report_model


def _final_result(risks):
    return {
        "role": "EMPLOYEE",
        "analysis_date": "2026-11-01",
        "session_id": "s1",
        "version_pins": {},
        "disclaimer": "d",
        "data_notice": "n",
        "clauses": [
            {
                "clause_id": "cl_0001",
                "original_text": "Điều 1. Thử việc 📄",
                "start_char": 0,
                "end_char": 17,
                "clause_labels": ["CONTRACT_TERM"],
            }
        ],
        "citations": [],
        "risks": risks,
    }


def _risk(clause_id):
    return {
        "clause_id": clause_id,
        "risk_labels": ["PROBATION"],
        "risk_basis": [{"label": "PROBATION", "basis_type": "UNFAVORABLE"}],
        "severity": "HIGH",
        "explanation": "x",
        "evidence_status": "SUPPORTED",
        "citation_ids": [],
    }


def test_unknown_clause_id_raises():
    with pytest.raises(ValueError, match="cl_9999"):
        build_report_model(_final_result([_risk("cl_9999")]))


def test_known_clause_keeps_original_text_with_non_bmp():
    model = build_report_model(_final_result([_risk("cl_0001")]))
    assert len(model.risks) == 1
    assert "📄" in model.risks[0].clause_quote
    assert model.no_risk_message is None


def test_empty_risks_gives_no_risk_message():
    model = build_report_model(_final_result([]))
    assert model.risks == []
    assert model.no_risk_message is not None
    assert "an toàn" not in model.no_risk_message
