"""Export DOCX từ ReportModel (C-21 b, TDD §16, FR-19/FR-25, BR-02). PDF là cut item 4 (cần chủ BRD duyệt).

Nội dung: tiêu đề, thông tin chung (vai trò, ngày phân tích, version tóm tắt), disclaimer + data notice (bắt
buộc), tóm tắt số liệu, từng rủi ro theo thứ tự xuất hiện: số Điều, trích nguyên văn (original_text), mức độ
hoặc "chưa đủ căn cứ" / "cần xem xét", loại căn cứ, giải thích, "Liên quan: Điều X", căn cứ pháp lý kèm
nguyên văn Khoản. Không có rủi ro ⇒ câu cố định, không dùng chữ "an toàn".
File chỉ tạo trong RAM (bytes), không ghi đĩa.
"""

from __future__ import annotations

import io

from docx import Document
from docx.shared import Pt

from app.result.report_model import ReportModel

EXPORT_VERSION = "export_docx_v1"
DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_VERSION_KEYS = ("extraction_version", "clause_taxonomy_version", "risk_taxonomy_version", "corpus_version",
                 "risk_prompt_version", "model_id", "app_commit")


def export_docx(model: ReportModel) -> bytes:
    doc = Document()
    doc.styles["Normal"].font.size = Pt(11)
    doc.add_heading(model.title, 0)

    info = model.general_info
    doc.add_paragraph(f"Vai trò phân tích: {info.role_label}")
    doc.add_paragraph(f"Ngày phân tích: {info.analysis_date}")
    pins = ", ".join(f"{k}={info.version_pins[k]}" for k in _VERSION_KEYS if k in info.version_pins)
    if pins:
        doc.add_paragraph(f"Phiên bản: {pins}").runs[0].font.size = Pt(8)

    doc.add_heading("Lưu ý", level=1)
    doc.add_paragraph(model.disclaimer)
    doc.add_paragraph(model.data_notice)

    if model.summary is not None:
        s = model.summary
        doc.add_heading("Tóm tắt", level=1)
        doc.add_paragraph(
            f"Số điều khoản: {s.clause_count}. Điều khoản có rủi ro: {s.risky_clause_count}. "
            f"Mức Cao: {s.high}, Trung bình: {s.medium}, Thấp: {s.low}. "
            f"Chưa đủ căn cứ: {s.insufficient}. Cần xem xét: {s.needs_review}.")

    doc.add_heading("Kết quả theo điều khoản", level=1)
    if model.no_risk_message:
        doc.add_paragraph(model.no_risk_message)
    for risk in model.risks:
        doc.add_heading(risk.clause_display, level=2)
        doc.add_paragraph(risk.clause_quote.strip(), style="Quote")
        if risk.needs_review:
            doc.add_paragraph(risk.status_message or "")
        else:
            labels = ", ".join(f"{b.label} ({b.basis_type_label})" for b in risk.risk_basis) or ", ".join(risk.risk_labels)
            doc.add_paragraph(f"Rủi ro: {labels}")
            if risk.show_severity_badge:
                doc.add_paragraph(f"Mức độ: {risk.severity_label}")
            else:
                doc.add_paragraph(f"Mức độ: {risk.severity_label}. {risk.status_message or ''}".strip())
        doc.add_paragraph(f"Giải thích: {risk.explanation}")
        if risk.related_displays:
            doc.add_paragraph("Liên quan: " + ", ".join(risk.related_displays))
        for c in risk.citations:
            if c.missing:
                doc.add_paragraph(f"Căn cứ: {c.citation_id} (không tìm thấy nội dung)")
                continue
            doc.add_paragraph(f"Căn cứ: {c.heading}")
            doc.add_paragraph(c.content).runs[0].italic = True

    doc.add_heading("Lưu ý", level=1)
    doc.add_paragraph(model.disclaimer)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
