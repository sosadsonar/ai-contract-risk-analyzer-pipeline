"""
export_docx.py — C-21(b): Xuất báo cáo DOCX từ ReportModel (TDD §16).

Quy tắc không được vi phạm:
- KHÔNG dùng chữ "an toàn" trong nội dung DOCX.
- KHÔNG hiện mã cl_xxxx ra giao diện người dùng.
- Nhãn điều khoản: dùng clause_number nếu có, ngược lại "Điều khoản thứ N" (đếm tuần tự).
- needs_review=True → hiện "Nghi ngờ, cần xem xét", bỏ qua severity và nhãn rủi ro.
- show_severity_badge=False (INSUFFICIENT_EVIDENCE) → hiện "Chưa đủ căn cứ", bỏ badge severity.
- citation.missing=True → bỏ qua citation đó (không hiện).
- related_clause_numbers: hiện "Liên quan: ..." nếu không rỗng.
- Cuối báo cáo: disclaimer + data_notice (FR-25).
- Chỉ xuất DOCX, không xuất PDF.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

if TYPE_CHECKING:
    from docx.text.paragraph import Paragraph

from app.result.report_model import ReportModel, RiskItem

# ---------------------------------------------------------------------------
# Nhãn tiếng Việt cho risk_labels (sao chép từ frontend/src/lib/labels.ts)
# ---------------------------------------------------------------------------

RISK_LABEL_VI: dict[str, str] = {
    "CONTRACT_TERM_TYPE": "Loại và thời hạn hợp đồng",
    "PROBATION": "Thử việc",
    "WAGE_AMOUNT_COMPONENTS": "Mức lương và các khoản cấu thành",
    "BONUS_BENEFITS": "Thưởng và phụ cấp",
    "PAYMENT_TIMING_METHOD": "Kỳ hạn và hình thức trả lương",
    "WORKING_HOURS_OVERTIME": "Giờ làm việc và làm thêm",
    "REST_AND_LEAVE": "Nghỉ ngơi và nghỉ phép",
    "SOCIAL_INSURANCE": "Bảo hiểm xã hội",
    "OSH_OBLIGATION": "An toàn vệ sinh lao động",
    "UNILATERAL_CHANGE": "Đơn phương thay đổi nội dung",
    "PENALTY_DEDUCTION_DAMAGES": "Phạt, khấu trừ, bồi thường",
    "DISCIPLINE_OBLIGATION": "Kỷ luật và nghĩa vụ",
    # Giữ nguyên nhãn gốc (X-15 chưa merge)
    "POST_EMPLOYMENT_RESTRICTION": "Ràng buộc sau khi nghỉ việc",
    "DEPOSIT_DOCUMENT_HELD": "Đặt cọc, giữ giấy tờ",
    "DISCRIMINATION_PROTECTED_GROUPS": "Phân biệt đối xử",
    "TRAINING_COMMITMENT": "Cam kết đào tạo",
    "TERMINATION_GROUNDS_NOTICE": "Căn cứ và thời hạn báo trước khi chấm dứt",
    "TERMINATION_SETTLEMENT": "Trợ cấp và thanh toán khi chấm dứt",
    "WAIVER_RIGHTS_DISPUTE": "Từ bỏ quyền, giải quyết tranh chấp",
    "PERSONAL_DATA_PRIVACY": "Dữ liệu cá nhân",
    "CONTRACT_FORM_RULES": "Hình thức hợp đồng, nội quy kèm theo",
}

BASIS_TYPE_VI: dict[str, str] = {
    "LEGAL_VIOLATION": "Trái quy định pháp luật",
    "UNFAVORABLE": "Bất lợi",
    "AMBIGUOUS": "Mơ hồ / thiếu rõ ràng",
}

SEVERITY_VI: dict[str | None, str] = {
    "HIGH": "Cao",
    "MEDIUM": "Trung bình",
    "LOW": "Thấp",
    None: "Chưa đủ căn cứ",
}

# Font hỗ trợ tiếng Việt (Unicode)
_FONT_NAME = "Times New Roman"


# ---------------------------------------------------------------------------
# Tiện ích định dạng
# ---------------------------------------------------------------------------


def _set_font(run, size_pt: int | None = None, bold: bool = False,
              italic: bool = False, color: RGBColor | None = None) -> None:
    """Đặt font Unicode hỗ trợ tiếng Việt cho run."""
    run.font.name = _FONT_NAME
    run.font.bold = bold
    run.font.italic = italic
    # Đặt cho cả phần Latin, Hán-Nôm và East Asian
    r_elem = run._r
    rPr = r_elem.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    rFonts.set(qn("w:ascii"), _FONT_NAME)
    rFonts.set(qn("w:hAnsi"), _FONT_NAME)
    rFonts.set(qn("w:eastAsia"), _FONT_NAME)
    rFonts.set(qn("w:cs"), _FONT_NAME)
    if size_pt is not None:
        run.font.size = Pt(size_pt)
    if color is not None:
        run.font.color.rgb = color


def _add_paragraph(doc: Document, text: str = "", style: str = "Normal",
                   size_pt: int = 11, bold: bool = False, italic: bool = False,
                   color: RGBColor | None = None, left_indent_cm: float = 0.0) -> "Paragraph":
    """Thêm đoạn văn với font tiếng Việt được đặt đúng."""
    p = doc.add_paragraph(style=style)
    if left_indent_cm:
        from docx.shared import Cm
        p.paragraph_format.left_indent = Cm(left_indent_cm)
    if text:
        run = p.add_run(text)
        _set_font(run, size_pt=size_pt, bold=bold, italic=italic, color=color)
    return p


def _add_heading_safe(doc: Document, text: str, level: int) -> "Paragraph":
    """Thêm heading với font tiếng Việt."""
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        _set_font(run)
    return p


# ---------------------------------------------------------------------------
# Hàm xuất chính
# ---------------------------------------------------------------------------


def export_docx(model: ReportModel) -> bytes:
    """
    Xuất ReportModel thành file DOCX và trả về bytes.

    Args:
        model: ReportModel đã build từ build_report_model().

    Returns:
        bytes nội dung file .docx.
    """
    doc = Document()

    # --- Tiêu đề báo cáo ---
    _add_heading_safe(doc, model.title, level=0)

    # --- Thông tin chung ---
    _add_heading_safe(doc, "Thông tin chung", level=1)
    gi = model.general_info
    _add_paragraph(doc, f"Vai trò: {gi.role_label}", size_pt=11)
    _add_paragraph(doc, f"Ngày phân tích: {gi.analysis_date}", size_pt=11)

    # --- Nội dung phân tích ---
    _add_heading_safe(doc, "Kết quả phân tích rủi ro", level=1)

    if model.no_risk_message:
        # Trường hợp không có rủi ro
        _add_paragraph(doc, model.no_risk_message, size_pt=11, italic=True)
    else:
        for idx, risk in enumerate(model.risks, start=1):
            _render_risk(doc, risk, idx)

    # --- Disclaimer và data_notice (bắt buộc FR-25) ---
    doc.add_paragraph()  # dòng trống trước
    _add_heading_safe(doc, "Lưu ý pháp lý", level=1)
    _add_paragraph(doc, model.disclaimer, size_pt=10, italic=True,
                   color=RGBColor(0x44, 0x44, 0x44))
    _add_paragraph(doc, model.data_notice, size_pt=10, italic=True,
                   color=RGBColor(0x44, 0x44, 0x44))

    # --- Lưu ra bytes ---
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def _get_clause_title(risk: RiskItem, sequential_index: int) -> str:
    """
    Trả về tiêu đề hiển thị của điều khoản.
    - Nếu có clause_number: dùng "Điều khoản: <clause_number>"
    - Ngược lại: "Điều khoản thứ <N>" (N = sequential_index, tính từ 1)
    KHÔNG hiện clause_id dạng cl_xxxx.
    """
    if risk.clause_number:
        return f"Điều khoản: {risk.clause_number}"
    return f"Điều khoản thứ {sequential_index}"


def _render_risk(doc: Document, risk: RiskItem, idx: int) -> None:
    """Render một RiskItem vào Document."""
    # Tiêu đề điều khoản (không hiện clause_id)
    clause_title = _get_clause_title(risk, idx)
    _add_heading_safe(doc, clause_title, level=2)

    # Trích dẫn văn bản điều khoản
    _add_paragraph(doc, f"Trích dẫn: {risk.clause_quote}", size_pt=10,
                   italic=True, color=RGBColor(0x33, 0x33, 0x66),
                   left_indent_cm=1.0)

    if risk.needs_review:
        # Trường hợp đặc biệt: không có nhãn rủi ro VÀ severity null
        _add_paragraph(doc, "Đánh giá: Nghi ngờ, cần xem xét", size_pt=11,
                       bold=True, color=RGBColor(0x99, 0x66, 0x00))
    else:
        # Nhãn rủi ro
        if risk.risk_labels:
            labels_vi = [RISK_LABEL_VI.get(lb, lb) for lb in risk.risk_labels]
            _add_paragraph(doc, f"Loại rủi ro: {', '.join(labels_vi)}", size_pt=11)

        # Mức độ rủi ro
        if risk.show_severity_badge:
            _add_paragraph(doc, f"Mức độ: {risk.severity_label}", size_pt=11, bold=True)
        else:
            # INSUFFICIENT_EVIDENCE hoặc severity null
            _add_paragraph(doc, "Mức độ: Chưa đủ căn cứ", size_pt=11, italic=True)

    # Phân tích / giải thích
    if risk.explanation:
        _add_paragraph(doc, f"Phân tích: {risk.explanation}", size_pt=11)

    # Căn cứ pháp lý
    visible_citations = [c for c in risk.citations if not c.missing]
    if visible_citations:
        _add_paragraph(doc, "Căn cứ pháp lý:", size_pt=11, bold=True)
        for citation in visible_citations:
            # Xây dựng tên văn bản: document_name + article
            doc_ref = citation.document_name
            if citation.article:
                doc_ref += f", Điều {citation.article}"
            if citation.clause:
                doc_ref += f", khoản {citation.clause}"
            # Nội dung trích dẫn
            cite_text = f"• {doc_ref}: {citation.content}" if citation.content else f"• {doc_ref}"
            _add_paragraph(doc, cite_text, size_pt=10, left_indent_cm=1.0)

    # Điều khoản liên quan
    if risk.related_clause_numbers:
        related_str = ", ".join(risk.related_clause_numbers)
        _add_paragraph(doc, f"Liên quan: {related_str}", size_pt=10, italic=True)

    # Căn cứ rủi ro (risk_basis)
    if risk.risk_basis and not risk.needs_review:
        basis_parts = []
        for rb in risk.risk_basis:
            basis_type_vi = BASIS_TYPE_VI.get(rb.basis_type, rb.basis_type)
            basis_parts.append(f"{rb.label} ({basis_type_vi})")
        if basis_parts:
            _add_paragraph(doc, f"Phân loại: {'; '.join(basis_parts)}", size_pt=10, italic=True)

    # Dòng phân cách
    doc.add_paragraph()

