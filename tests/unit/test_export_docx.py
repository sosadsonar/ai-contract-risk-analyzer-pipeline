"""
tests/unit/test_export_docx.py — C-21(b): pytest cho export_docx.

Đối chiếu danh sách test (a)–(h):
  a. Xuất thành công: bytes hợp lệ, không rỗng, bắt đầu bằng PK, parse được bởi python-docx.
  b. Tiêu đề + thông tin chung: title, role_label, analysis_date trong văn bản.
  c. Có rủi ro: nhãn tiếng Việt, severity hiện đúng, không hiện cl_xxxx, không có 'an toàn'.
  d. No-risk: NO_RISK_MESSAGE xuất hiện, tuyệt đối không dùng từ 'an toàn'.
  e. INSUFFICIENT_EVIDENCE: 'Chưa đủ căn cứ' hiện thay vì mức độ cụ thể.
  f. needs_review=True: 'Nghi ngờ, cần xem xét' hiện, không có nhãn rủi ro hay badge severity.
  g. citation.missing=True: citation bị bỏ qua hoàn toàn, không crash.
  h. related_clause_numbers & clause_number: 'Liên quan:' xuất hiện; clause_number dùng thay cho 'Điều khoản thứ N'.
     Bổ sung:
     - related_clause_ids với id lạ không gây lỗi (safe lookup).
     - Ký tự emoji ngoài BMP (📄) còn nguyên vẹn trong DOCX.
     - Thứ tự hiển thị các rủi ro theo start_char tăng dần.
"""

from __future__ import annotations

import copy
import io
import json
import re
from pathlib import Path
from typing import Any

import pytest
from docx import Document as DocxDocument

from app.result.export_docx import export_docx
from app.result.report_model import (
    NO_RISK_MESSAGE,
    CitationRef,
    GeneralInfo,
    ReportModel,
    RiskBasisItem,
    RiskItem,
    build_report_model,
)

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "mock_final_result_v1.json"


@pytest.fixture(scope="module")
def base_result() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _full_text(docx_bytes: bytes) -> str:
    """Trả về toàn bộ văn bản của DOCX (nối các paragraph bằng newline)."""
    doc = DocxDocument(io.BytesIO(docx_bytes))
    return "\n".join(p.text for p in doc.paragraphs)


def _make_model(
    risks: list[RiskItem] | None = None,
    no_risk_message: str | None = None,
) -> ReportModel:
    """Tạo ReportModel tối giản để test."""
    gi = GeneralInfo(
        role="EMPLOYEE",
        role_label="Người lao động",
        analysis_date="2026-11-13",
        session_id="test-session",
        version_pins={},
    )
    if risks is None:
        risks = []
    if no_risk_message is None and not risks:
        no_risk_message = NO_RISK_MESSAGE
    return ReportModel(
        title="Phân tích rủi ro hợp đồng lao động",
        general_info=gi,
        risks=risks,
        no_risk_message=no_risk_message,
        disclaimer="Kết quả chỉ hỗ trợ tham khảo, không thay thế tư vấn pháp lý.",
        data_notice="Dữ liệu được xử lý trong bộ nhớ tạm thời.",
    )


def _make_basic_risk(
    clause_quote: str = "Điều 1. Công ty giữ văn bằng.",
    risk_labels: list[str] | None = None,
    severity_raw: str | None = "HIGH",
    evidence_status: str = "SUPPORTED",
    citations: list[CitationRef] | None = None,
    needs_review: bool = False,
    clause_number: str | None = None,
    related_clause_numbers: list[str] | None = None,
    clause_start_char: int = 0,
) -> RiskItem:
    return RiskItem(
        clause_id="cl_0001",
        clause_quote=clause_quote,
        clause_start_char=clause_start_char,
        risk_labels=risk_labels if risk_labels is not None else ["DEPOSIT_DOCUMENT_HELD"],
        risk_basis=[RiskBasisItem(label="DEPOSIT_DOCUMENT_HELD", basis_type="LEGAL_VIOLATION")],
        severity_raw=severity_raw,
        severity_label="Cao" if severity_raw == "HIGH" else "chưa đủ căn cứ",
        show_severity_badge=(severity_raw is not None and evidence_status != "INSUFFICIENT_EVIDENCE"),
        explanation="Giải thích rủi ro kiểm thử.",
        evidence_status=evidence_status,
        citations=citations if citations is not None else [],
        needs_review=needs_review,
        clause_number=clause_number,
        related_clause_numbers=related_clause_numbers if related_clause_numbers is not None else [],
    )


# ---------------------------------------------------------------------------
# Test cases chính (a)–(h)
# ---------------------------------------------------------------------------


def test_a_export_returns_valid_docx_bytes(base_result):
    """(a) export_docx() trả về bytes hợp lệ, bắt đầu bằng PK (ZIP), parse được bởi python-docx."""
    model = build_report_model(base_result)
    result = export_docx(model)

    assert isinstance(result, bytes), "Kết quả phải là bytes"
    assert len(result) > 0, "Bytes không được rỗng"
    assert result[:2] == b"PK", "DOCX phải bắt đầu bằng PK (magic bytes của ZIP header)"

    doc = DocxDocument(io.BytesIO(result))
    assert len(doc.paragraphs) > 0, "DOCX phải có ít nhất một đoạn văn"


def test_b_title_and_general_info(base_result):
    """(b) Title, role_label, analysis_date phải xuất hiện trong văn bản DOCX."""
    model = build_report_model(base_result)
    result = export_docx(model)
    text = _full_text(result)

    assert "Phân tích rủi ro hợp đồng lao động" in text, "Thiếu tiêu đề báo cáo"
    assert "Người lao động" in text, "Thiếu role_label"
    assert "2026-10-12" in text, "Thiếu analysis_date"


def test_c_risk_labels_vi_no_raw_id(base_result):
    """(c) Nhãn rủi ro hiện bằng tiếng Việt; không hiện mã cl_xxxx; không có từ 'an toàn'."""
    model = build_report_model(base_result)
    result = export_docx(model)
    text = _full_text(result)

    # Nhãn tiếng Việt
    assert "Đặt cọc, giữ giấy tờ" in text, "Thiếu nhãn tiếng Việt DEPOSIT_DOCUMENT_HELD"
    # Mức độ "Cao"
    assert "Cao" in text, "Thiếu severity label 'Cao'"
    # Tuyệt đối không chứa chuỗi cl_
    assert "cl_" not in text, "Không được chứa chuỗi 'cl_' trong DOCX"
    # Không dùng chữ "an toàn" trong nhận định
    assert "an toàn" not in text.lower(), "Báo cáo fixture không được chứa từ 'an toàn'"


def test_d_no_risk_message_no_safe_word():
    """(d) Khi không có rủi ro: NO_RISK_MESSAGE xuất hiện; tuyệt đối không dùng từ 'an toàn'."""
    model = _make_model(risks=[], no_risk_message=NO_RISK_MESSAGE)
    result = export_docx(model)
    text = _full_text(result)

    assert NO_RISK_MESSAGE in text, f"Thiếu NO_RISK_MESSAGE: '{NO_RISK_MESSAGE}'"
    assert "an toàn" not in NO_RISK_MESSAGE, "NO_RISK_MESSAGE không được chứa 'an toàn'"
    assert "an toàn" not in text.lower(), "Toàn bộ báo cáo không rủi ro không được chứa từ 'an toàn'"
    assert "cl_" not in text, "Báo cáo không rủi ro không được chứa chuỗi 'cl_'"


def test_e_insufficient_evidence():
    """(e) INSUFFICIENT_EVIDENCE: hiện 'Chưa đủ căn cứ', không hiện badge severity cụ thể."""
    risk = _make_basic_risk(
        severity_raw=None,
        evidence_status="INSUFFICIENT_EVIDENCE",
    )
    risk.show_severity_badge = False
    risk.severity_label = "chưa đủ căn cứ"

    model = _make_model(risks=[risk], no_risk_message=None)
    result = export_docx(model)
    text = _full_text(result)

    assert "Chưa đủ căn cứ" in text, "Thiếu 'Chưa đủ căn cứ' cho INSUFFICIENT_EVIDENCE"
    assert "Mức độ: Cao" not in text
    assert "Mức độ: Trung bình" not in text
    assert "Mức độ: Thấp" not in text


def test_f_needs_review():
    """(f) needs_review=True: 'Nghi ngờ, cần xem xét' hiện; không hiện nhãn rủi ro/severity."""
    risk = _make_basic_risk(
        risk_labels=[],
        severity_raw=None,
        needs_review=True,
    )
    risk.show_severity_badge = False
    risk.severity_label = "chưa đủ căn cứ"

    model = _make_model(risks=[risk], no_risk_message=None)
    result = export_docx(model)
    text = _full_text(result)

    assert "Nghi ngờ, cần xem xét" in text, "Thiếu 'Nghi ngờ, cần xem xét' cho needs_review"
    assert "Loại rủi ro:" not in text, "Không được hiện nhãn rủi ro khi needs_review"
    assert "Mức độ: Cao" not in text
    assert "Mức độ: Chưa đủ căn cứ" not in text


def test_g_missing_citation_skipped():
    """(g) citation.missing=True → bỏ qua hoàn toàn, không crash, không xuất hiện trong văn bản."""
    missing_cite = CitationRef(
        citation_id="MISSING_CIT_001",
        document_name="",
        article="",
        content="",
        missing=True,
    )
    visible_cite = CitationRef(
        citation_id="VISIBLE_CIT_001",
        document_name="Bộ luật Lao động 2019",
        article="17",
        content="Người sử dụng lao động không được giữ giấy tờ.",
        missing=False,
    )
    risk = _make_basic_risk(citations=[missing_cite, visible_cite])

    model = _make_model(risks=[risk], no_risk_message=None)
    result = export_docx(model)
    text = _full_text(result)

    assert "MISSING_CIT_001" not in text, "citation.missing=True không được hiện trong DOCX"
    assert "Bộ luật Lao động 2019" in text, "Citation visible phải hiện trong DOCX"


def test_h_related_clause_numbers_and_clause_number():
    """(h) related_clause_numbers hiện 'Liên quan:'; clause_number dùng thay 'Điều khoản thứ N'."""
    risk = _make_basic_risk(
        clause_number="Điều 5",
        related_clause_numbers=["Điều 7", "Điều 9"],
    )

    model = _make_model(risks=[risk], no_risk_message=None)
    result = export_docx(model)
    text = _full_text(result)

    assert "Điều khoản: Điều 5" in text, "Thiếu clause_number trong tiêu đề điều khoản"
    assert "Điều khoản thứ 1" not in text, "Không dùng 'thứ N' khi đã có clause_number"
    assert "Liên quan: Điều 7, Điều 9" in text, "Thiếu dòng 'Liên quan: Điều 7, Điều 9'"


def test_h_no_clause_number_uses_sequential():
    """(h phụ) Khi không có clause_number, dùng 'Điều khoản thứ N' theo thứ tự."""
    risk1 = _make_basic_risk(clause_number=None, clause_start_char=0)
    risk2 = _make_basic_risk(clause_number=None, clause_start_char=100)
    risk2.clause_id = "cl_0002"

    model = _make_model(risks=[risk1, risk2], no_risk_message=None)
    result = export_docx(model)
    text = _full_text(result)

    assert "Điều khoản thứ 1" in text, "Thiếu 'Điều khoản thứ 1'"
    assert "Điều khoản thứ 2" in text, "Thiếu 'Điều khoản thứ 2'"


# ---------------------------------------------------------------------------
# Bổ sung các bài kiểm tra theo mục 3 yêu cầu gốc
# ---------------------------------------------------------------------------


def test_related_clause_ids_with_unknown_id(base_result):
    """related_clause_ids chứa id lạ không gây lỗi, bỏ qua an toàn hoặc dùng số thứ tự."""
    data = copy.deepcopy(base_result)
    # Thêm related_clause_ids gồm 1 id lạ và 1 id có thật
    data["risks"][0]["related_clause_ids"] = ["cl_UNKNOWN_9999", "cl_0002"]

    model = build_report_model(data)
    assert len(model.risks) >= 1
    # Không crash, id lạ bị bỏ qua
    assert "cl_UNKNOWN_9999" not in model.risks[0].related_clause_numbers

    # Export DOCX không crash và không chứa cl_
    docx_bytes = export_docx(model)
    text = _full_text(docx_bytes)
    assert "cl_" not in text
    assert "cl_UNKNOWN_9999" not in text


def test_emoji_bmp_preserved():
    """Ký tự ngoài BMP (📄) còn nguyên vẹn trong DOCX và file bắt đầu bằng PK."""
    emoji_text = "Điều 2. Địa điểm làm việc thỏa thuận kèm tài liệu. 📄"
    risk = _make_basic_risk(clause_quote=emoji_text)

    model = _make_model(risks=[risk])
    docx_bytes = export_docx(model)

    assert docx_bytes[:2] == b"PK", "File bắt đầu bằng magic bytes PK"
    text = _full_text(docx_bytes)
    assert "📄" in text, "Ký tự emoji 📄 phải được bảo toàn nguyên vẹn trong DOCX"


def test_risks_ordered_by_start_char(base_result):
    """Rủi ro trong DOCX xuất hiện đúng thứ tự start_char tăng dần."""
    data = copy.deepcopy(base_result)
    # Tạo 2 clauses và 2 risks với thứ tự trong data bị đảo ngược
    data["clauses"] = [
        {"clause_id": "cl_0001", "original_text": "Nội dung điều 1", "start_char": 0, "end_char": 20},
        {"clause_id": "cl_0002", "original_text": "Nội dung điều 2", "start_char": 50, "end_char": 80},
    ]
    data["risks"] = [
        {
            "clause_id": "cl_0002",
            "risk_labels": ["TERMINATION_GROUNDS_NOTICE"],
            "risk_basis": [{"label": "TERMINATION_GROUNDS_NOTICE", "basis_type": "UNFAVORABLE"}],
            "severity": "MEDIUM",
            "explanation": "Rủi ro điều 2",
            "evidence_status": "SUPPORTED",
            "citation_ids": [],
        },
        {
            "clause_id": "cl_0001",
            "risk_labels": ["PROBATION"],
            "risk_basis": [{"label": "PROBATION", "basis_type": "LEGAL_VIOLATION"}],
            "severity": "HIGH",
            "explanation": "Rủi ro điều 1",
            "evidence_status": "SUPPORTED",
            "citation_ids": [],
        },
    ]

    model = build_report_model(data)
    docx_bytes = export_docx(model)
    text = _full_text(docx_bytes)

    # Điều khoản thứ 1 (start_char=0) phải xuất hiện trước Điều khoản thứ 2 (start_char=50)
    pos_item1 = text.find("Nội dung điều 1")
    pos_item2 = text.find("Nội dung điều 2")
    assert pos_item1 != -1 and pos_item2 != -1
    assert pos_item1 < pos_item2, "Rủi ro start_char nhỏ hơn phải xuất hiện trước"
    assert "cl_" not in text
