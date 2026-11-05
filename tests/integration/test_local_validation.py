"""Real PDF/DOCX → canonical → scope → mask → segment, without dev fixture results."""

import pymupdf
import pytest
from app.core.config import Settings
from app.domain.errors import ValidationReject
from app.session.local_validation import validate_local
from docx import Document


def _pdf(path, text):
    doc = pymupdf.open()
    page = doc.new_page()
    remaining, _ = page.insert_htmlbox(
        pymupdf.Rect(40, 40, 550, 800),
        '<div style="font-size:12pt; white-space:pre-line">'
        + text.replace("\n", "<br>") + "</div>",
    )
    assert remaining >= 0
    doc.save(path)
    doc.close()
    return path


@pytest.mark.asyncio
async def test_real_pdf_validation_preserves_offsets_and_masks_before_segmentation(tmp_path):
    path = _pdf(tmp_path / "labor.pdf", (
        "HỢP ĐỒNG LAO ĐỘNG\n"
        "Người lao động và người sử dụng lao động thỏa thuận về công việc và tiền lương.\n"
        "Điện thoại: 0912345678.\n"
        "Điều 1. Công việc\n"
        "Người lao động thực hiện công việc theo hợp đồng lao động tại nơi làm việc đã thỏa thuận.\n"
        "Điều 2. Tiền lương\n"
        "Người sử dụng lao động trả lương theo thời hạn đã ghi trong hợp đồng lao động."
    ))
    output = await validate_local(path, path.name, Settings(_env_file=None))
    canonical = output.extraction.canonical_text
    masked = output.masking.masked_text
    assert output.scope.accept
    assert "0912345678" in canonical and "0912345678" not in masked
    assert len(canonical) == len(masked)
    assert any(c.structure.number == "2" for c in output.segmentation.clauses)
    previous_end = 0
    for clause in output.segmentation.clauses:
        assert clause.start_char >= previous_end
        assert clause.original_text == canonical[clause.start_char:clause.end_char]
        assert all(not (span.start < boundary < span.end)
                   for span in output.masking.pii_spans
                   for boundary in (clause.start_char, clause.end_char))
        previous_end = clause.end_char


@pytest.mark.asyncio
async def test_out_of_scope_pdf_rejects_before_masking_or_segmentation(tmp_path):
    path = _pdf(tmp_path / "invoice.pdf", (
        "HÓA ĐƠN MUA BÁN\n"
        "Bên mua và bên bán xác nhận giao dịch mua bán hàng hóa theo giá và số lượng đã thỏa thuận.\n"
        "Tổng tiền thanh toán theo hóa đơn là 1000000 đồng, thực hiện chuyển khoản hôm nay."
    ))
    with pytest.raises(ValidationReject) as rejected:
        await validate_local(path, path.name, Settings(_env_file=None))
    assert rejected.value.code == "NOT_LABOR_CONTRACT"


@pytest.mark.asyncio
async def test_real_pdf_clause_limit_rejects_at_segment_stage(tmp_path):
    path = _pdf(tmp_path / "labor.pdf", (
        "HỢP ĐỒNG LAO ĐỘNG\n"
        "Người lao động và người sử dụng lao động thỏa thuận về công việc và tiền lương.\n"
        "Điều 1. Công việc\n"
        "Người lao động thực hiện công việc tại văn phòng theo thời hạn ghi trong hợp đồng.\n"
        "Điều 2. Tiền lương\n"
        "Người sử dụng lao động trả tiền lương hàng tháng theo thỏa thuận giữa các bên."
    ))
    with pytest.raises(ValidationReject) as rejected:
        await validate_local(path, path.name, Settings(_env_file=None, MAX_CLAUSES=1))
    assert rejected.value.code == "TOO_MANY_CLAUSES"


@pytest.mark.asyncio
async def test_docx_validation_masks_pii_and_preserves_canonical_clause_offsets(tmp_path):
    path = tmp_path / "labor.docx"
    doc = Document()
    doc.add_paragraph("HỢP ĐỒNG LAO ĐỘNG")
    doc.add_paragraph("Người lao động và người sử dụng lao động thỏa thuận công việc và tiền lương.")
    doc.add_paragraph("Điều 1. Công việc")
    doc.add_paragraph("Người lao động thực hiện công việc theo hợp đồng; điện thoại: 0912345678.")
    doc.add_paragraph("Điều 2. Tiền lương")
    doc.add_paragraph("Người sử dụng lao động trả lương hàng tháng theo thỏa thuận trong hợp đồng.")
    doc.save(path)

    output = await validate_local(path, path.name, Settings(_env_file=None))
    canonical = output.extraction.canonical_text
    masked = output.masking.masked_text
    assert output.scope.accept and output.extraction.page_count is None
    assert len(masked) == len(canonical)
    assert "0912345678" in canonical and "0912345678" not in masked
    assert [c.structure.number for c in output.segmentation.clauses if c.structure.number] == ["1", "2"]
    assert all(c.original_text == canonical[c.start_char:c.end_char] for c in output.segmentation.clauses)
    assert all(not (span.start < boundary < span.end)
               for c in output.segmentation.clauses
               for boundary in (c.start_char, c.end_char)
               for span in output.masking.pii_spans)
