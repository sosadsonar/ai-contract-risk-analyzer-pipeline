"""
tests/unit/test_report_model.py — C-21(a): pytest cho build_report_model.

Các ca kiểm tra:
  1. Fixture chuẩn (mock_final_result_v1.json): có rủi ro, đúng thứ tự, đúng citation.
  2. INSUFFICIENT_EVIDENCE: severity=null, show_severity_badge=False, severity_label="chưa đủ căn cứ".
  3. Rủi ro rỗng (risks=[]): no_risk_message đúng, không dùng chữ "an toàn".
  4. Ký tự ngoài BMP (📄) trong original_text: không bị lỗi, quote giữ nguyên.
  5. citation_id không tìm thấy: missing=True, không bỏ qua im lặng.
  6. Thiếu disclaimer / data_notice: raise ValueError.
"""

from __future__ import annotations

import copy
import json
import logging
from pathlib import Path

import pytest

from app.result.report_model import (
    NO_RISK_MESSAGE,
    ReportModel,
    build_report_model,
)

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "mock_final_result_v1.json"


@pytest.fixture(scope="module")
def base_result() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Ca 1: Fixture chuẩn — có rủi ro, cấu trúc đầy đủ
# ---------------------------------------------------------------------------


def test_fixture_has_risks(base_result):
    model = build_report_model(base_result)
    assert isinstance(model, ReportModel)
    assert model.title == "Phân tích rủi ro hợp đồng lao động"
    assert model.no_risk_message is None, "Fixture có rủi ro thì no_risk_message phải None"
    assert len(model.risks) >= 1


def test_disclaimer_and_data_notice(base_result):
    model = build_report_model(base_result)
    assert model.disclaimer, "disclaimer bắt buộc (FR-25)"
    assert model.data_notice, "data_notice bắt buộc (FR-25)"


def test_general_info(base_result):
    model = build_report_model(base_result)
    assert model.general_info.role == "EMPLOYEE"
    assert model.general_info.role_label == "Người lao động"
    assert model.general_info.analysis_date == "2026-10-12"


def test_risk_order_by_start_char(base_result):
    """Rủi ro phải được sắp xếp theo start_char tăng dần."""
    model = build_report_model(base_result)
    starts = [r.clause_start_char for r in model.risks]
    assert starts == sorted(starts), f"Rủi ro chưa sắp theo start_char: {starts}"


def test_citation_resolved(base_result):
    """Mọi citation_id trong risks phải được tra thành CitationRef đầy đủ."""
    model = build_report_model(base_result)
    for risk in model.risks:
        for cite in risk.citations:
            assert not cite.missing, (
                f"citation_id '{cite.citation_id}' trong clause '{risk.clause_id}' "
                f"không tìm thấy trong citations"
            )
            assert cite.document_name, "document_name rỗng"


def test_clause_quote_uses_original_text(base_result):
    """clause_quote phải lấy từ original_text, không phải masked text."""
    model = build_report_model(base_result)
    clause_map = {c["clause_id"]: c for c in base_result["clauses"]}
    for risk in model.risks:
        expected = clause_map[risk.clause_id]["original_text"]
        assert risk.clause_quote == expected, (
            f"Clause {risk.clause_id}: quote không khớp original_text"
        )


def test_risk_basis_items(base_result):
    model = build_report_model(base_result)
    for risk in model.risks:
        assert risk.risk_basis, "risk_basis không được rỗng"
        for rb in risk.risk_basis:
            assert rb.label
            assert rb.basis_type
            assert rb.basis_type_label  # phải có nhãn tiếng Việt


# ---------------------------------------------------------------------------
# Ca 2: INSUFFICIENT_EVIDENCE
# ---------------------------------------------------------------------------


def test_insufficient_evidence_no_badge(base_result):
    """
    Risk với evidence_status='INSUFFICIENT_EVIDENCE' và severity=null:
    show_severity_badge=False, severity_label='chưa đủ căn cứ'.
    """
    data = copy.deepcopy(base_result)
    # Đổi risk đầu tiên thành INSUFFICIENT_EVIDENCE
    data["risks"][0]["evidence_status"] = "INSUFFICIENT_EVIDENCE"
    data["risks"][0]["severity"] = None
    data["risks"][0]["citation_ids"] = []
    model = build_report_model(data)
    risk = next(r for r in model.risks if r.clause_id == data["risks"][0]["clause_id"])
    assert not risk.show_severity_badge, "INSUFFICIENT_EVIDENCE không được hiện badge"
    assert risk.severity_label == "chưa đủ căn cứ"
    assert risk.severity_raw is None


def test_severity_null_no_badge(base_result):
    """severity=null bất kể evidence_status: không hiện badge."""
    data = copy.deepcopy(base_result)
    data["risks"][0]["severity"] = None
    data["risks"][0]["evidence_status"] = "SUPPORTED"
    model = build_report_model(data)
    risk = next(r for r in model.risks if r.clause_id == data["risks"][0]["clause_id"])
    assert not risk.show_severity_badge


def test_supported_risk_shows_badge(base_result):
    """Risk SUPPORTED với severity HIGH: show_severity_badge=True."""
    model = build_report_model(base_result)
    # Fixture có risk severity=HIGH
    supported = [r for r in model.risks if r.evidence_status == "SUPPORTED"]
    if supported:
        assert supported[0].show_severity_badge
        assert supported[0].severity_label in ("Cao", "Trung bình", "Thấp")


# ---------------------------------------------------------------------------
# Ca 3: Rủi ro rỗng (risks=[])
# ---------------------------------------------------------------------------


def test_no_risks_message(base_result):
    """Khi risks=[], no_risk_message phải là câu quy định; không dùng 'an toàn'."""
    data = copy.deepcopy(base_result)
    data["risks"] = []
    model = build_report_model(data)
    assert model.risks == [], "risks phải là list rỗng"
    assert model.no_risk_message == NO_RISK_MESSAGE
    assert "an toàn" not in model.no_risk_message.lower(), (
        f"Không được dùng chữ 'an toàn': '{model.no_risk_message}'"
    )
    assert "Không phát hiện" in model.no_risk_message


def test_no_risks_still_has_disclaimer(base_result):
    """Dù risks rỗng, disclaimer và data_notice vẫn bắt buộc."""
    data = copy.deepcopy(base_result)
    data["risks"] = []
    model = build_report_model(data)
    assert model.disclaimer
    assert model.data_notice


# ---------------------------------------------------------------------------
# Ca 4: Ký tự ngoài BMP (📄) — INV-12
# ---------------------------------------------------------------------------


def test_non_bmp_character_in_original_text(base_result):
    """
    Fixture mock_final_result_v1.json đã chứa ký tự 📄 (U+1F4C4) ở clause 2.
    original_text phải giữ nguyên ký tự, clause_quote phải khớp chính xác.
    """
    data = copy.deepcopy(base_result)
    # Thêm risk cho clause chứa 📄
    non_bmp_clause = next(
        (c for c in data["clauses"] if "📄" in c.get("original_text", "")), None
    )
    if non_bmp_clause is None:
        pytest.skip("Fixture không có clause chứa ký tự 📄 ngoài BMP")

    data["risks"].append({
        "clause_id": non_bmp_clause["clause_id"],
        "risk_labels": ["WORKING_CONDITIONS"],
        "risk_basis": [{"label": "WORKING_CONDITIONS", "basis_type": "UNFAVORABLE"}],
        "severity": "LOW",
        "explanation": "Test non-BMP",
        "evidence_status": "SUPPORTED",
        "citation_ids": [],
    })
    model = build_report_model(data)
    risk = next(r for r in model.risks if r.clause_id == non_bmp_clause["clause_id"])
    assert "📄" in risk.clause_quote, "Ký tự ngoài BMP (📄) bị mất trong clause_quote"
    # Kiểm tra không bị lỗi khi đếm len (Python str đếm code points)
    assert len(risk.clause_quote) > 0


def test_non_bmp_in_canonical_text(base_result):
    """canonical_text chứa 📄: build_report_model không crash."""
    data = copy.deepcopy(base_result)
    assert "📄" in data["canonical_text"], "Fixture thiếu 📄 trong canonical_text"
    model = build_report_model(data)
    assert model is not None


# ---------------------------------------------------------------------------
# Ca 5: citation_id không tìm thấy
# ---------------------------------------------------------------------------


def test_missing_citation_id_marked_not_silent(base_result, caplog):
    """
    citation_id không có trong citations: missing=True và ghi log warning.
    Không được bỏ qua im lặng.
    """
    data = copy.deepcopy(base_result)
    data["risks"][0]["citation_ids"] = ["GHOST_CITATION_NOT_EXIST"]
    with caplog.at_level(logging.WARNING, logger="app.result.report_model"):
        model = build_report_model(data)
    risk = next(r for r in model.risks if r.clause_id == data["risks"][0]["clause_id"])
    assert any(c.missing for c in risk.citations), (
        "citation_id không tồn tại phải được đánh dấu missing=True"
    )
    assert any("GHOST_CITATION_NOT_EXIST" in r.message for r in caplog.records), (
        "Phải có log warning cho citation_id không tìm thấy"
    )


# ---------------------------------------------------------------------------
# Ca 6: Thiếu disclaimer / data_notice → raise ValueError
# ---------------------------------------------------------------------------


def test_missing_disclaimer_raises(base_result):
    data = copy.deepcopy(base_result)
    del data["disclaimer"]
    with pytest.raises(ValueError, match="disclaimer"):
        build_report_model(data)


def test_missing_data_notice_raises(base_result):
    data = copy.deepcopy(base_result)
    del data["data_notice"]
    with pytest.raises(ValueError, match="data_notice"):
        build_report_model(data)


def test_empty_disclaimer_raises(base_result):
    data = copy.deepcopy(base_result)
    data["disclaimer"] = ""
    with pytest.raises(ValueError, match="disclaimer"):
        build_report_model(data)

