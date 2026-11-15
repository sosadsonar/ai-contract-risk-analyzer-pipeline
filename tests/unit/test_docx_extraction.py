"""DOCX document-order, numbering, accepted revisions and canonical limits (C-08b)."""

import json
import unicodedata
from pathlib import Path

import pytest
from app.core.enums import Role
from app.document.extractor import detect_kind, extract
from app.domain.errors import ValidationReject
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]


def _revision(paragraph, kind, text):
    wrapper = OxmlElement(f"w:{kind}")
    run = OxmlElement("w:r")
    value = OxmlElement("w:delText" if kind in ("del", "moveFrom") else "w:t")
    value.text = text
    run.append(value)
    wrapper.append(run)
    paragraph._p.append(wrapper)


def _textbox(paragraph, text):
    run = OxmlElement("w:r")
    drawing = OxmlElement("w:drawing")
    content = OxmlElement("w:txbxContent")
    inner = OxmlElement("w:p")
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = text
    r.append(t)
    inner.append(r)
    content.append(inner)
    drawing.append(content)
    run.append(drawing)
    paragraph._p.append(run)


def test_docx_document_order_numbering_revisions_and_textbox(tmp_path):
    doc = Document()
    doc.add_paragraph("HỢP ĐỒNG LAO ĐỘNG")
    first = doc.add_paragraph("Người lao động thực hiện công việc theo thỏa thuận.", style="List Number")
    _revision(first, "del", "PHẢI BỎ")
    _revision(first, "ins", " Văn bản được chấp nhận.")
    _revision(first, "moveFrom", "CHUYỂN ĐI")
    _revision(first, "moveTo", " Nội dung chuyển đến.")
    table = doc.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Lương"
    table.cell(0, 1).text = "12.000.000 đồng/tháng"
    second = doc.add_paragraph("Người sử dụng lao động trả lương theo hợp đồng.", style="List Number")
    _textbox(second, "Ghi chú trong hộp văn bản gần điều khoản lương.")
    doc.add_paragraph("Điện thoại: 0912345678. Nghĩa vụ của hai bên được xác định rõ.")
    doc.sections[0].header.paragraphs[0].text = "Không nằm trong canonical text"
    path = tmp_path / "labor.docx"
    doc.save(path)

    result = extract(path, detect_kind(path, path.name))
    expected = (
        "HỢP ĐỒNG LAO ĐỘNG\n"
        "1. Người lao động thực hiện công việc theo thỏa thuận. Văn bản được chấp nhận. Nội dung chuyển đến.\n"
        "Lương | 12.000.000 đồng/tháng\n"
        "2. Người sử dụng lao động trả lương theo hợp đồng.\n"
        "Ghi chú trong hộp văn bản gần điều khoản lương.\n"
        "Điện thoại: 0912345678. Nghĩa vụ của hai bên được xác định rõ."
    )
    assert result.canonical_text == expected
    assert result == extract(path, "docx")
    assert result.extraction_version == "extract_docx_v2"
    assert result.page_count is None and result.char_count == len(expected)
    assert unicodedata.is_normalized("NFC", expected)
    artifact = result.to_artifact(path.name, Role.EMPLOYEE)
    assert "page_count" not in artifact
    schema = json.loads((ROOT / "ai_pipeline/schemas/extraction_v1.json").read_text(encoding="utf-8"))
    assert not list(Draft202012Validator(schema).iter_errors(artifact))


def test_multilevel_numbering_resets_children_and_honors_start_override(tmp_path):
    doc = Document()
    root = doc.part.numbering_part.element
    abstract_id = max(int(el.get(qn("w:abstractNumId"))) for el in root.findall(qn("w:abstractNum"))) + 1
    num_id = max(int(el.get(qn("w:numId"))) for el in root.findall(qn("w:num"))) + 1
    abstract = OxmlElement("w:abstractNum")
    abstract.set(qn("w:abstractNumId"), str(abstract_id))
    for index, fmt, template in ((0, "decimal", "%1."), (1, "lowerLetter", "%1.%2)")):
        level = OxmlElement("w:lvl")
        level.set(qn("w:ilvl"), str(index))
        for tag, value in (("start", "1"), ("numFmt", fmt), ("lvlText", template)):
            child = OxmlElement(f"w:{tag}")
            child.set(qn("w:val"), value)
            level.append(child)
        abstract.append(level)
    root.append(abstract)
    num = OxmlElement("w:num")
    num.set(qn("w:numId"), str(num_id))
    link = OxmlElement("w:abstractNumId")
    link.set(qn("w:val"), str(abstract_id))
    num.append(link)
    override = OxmlElement("w:lvlOverride")
    override.set(qn("w:ilvl"), "0")
    start = OxmlElement("w:startOverride")
    start.set(qn("w:val"), "3")
    override.append(start)
    num.append(override)
    root.append(num)
    doc.add_paragraph("Hợp đồng lao động với người lao động và người sử dụng lao động.")
    for level, phrase in ((0, "Công việc thực hiện theo thời hạn đã thỏa thuận."),
                          (1, "Điều khoản chi tiết về vị trí làm việc và trách nhiệm."),
                          (1, "Điều khoản chi tiết về nghĩa vụ tại nơi làm việc."),
                          (0, "Tiền lương trả theo kỳ hàng tháng quy định trong hợp đồng."),
                          (1, "Mức lương trả qua chuyển khoản ngân hàng theo thỏa thuận.")):
        paragraph = doc.add_paragraph(phrase)
        properties = paragraph._p.get_or_add_pPr()
        num_pr = OxmlElement("w:numPr")
        ilvl = OxmlElement("w:ilvl")
        ilvl.set(qn("w:val"), str(level))
        num_ref = OxmlElement("w:numId")
        num_ref.set(qn("w:val"), str(num_id))
        num_pr.extend((ilvl, num_ref))
        properties.append(num_pr)
    path = tmp_path / "numbered.docx"
    doc.save(path)
    text = extract(path, "docx").canonical_text
    assert "\n3. Công việc" in text
    assert "\n3.a) Điều khoản" in text
    assert "\n3.b) Điều khoản" in text
    assert "\n4. Tiền lương" in text
    assert "\n4.a) Mức lương" in text


def test_block_revisions_and_bullet_markers_use_accepted_document_order(tmp_path):
    doc = Document()
    doc.add_paragraph("Hợp đồng lao động do người lao động và người sử dụng lao động cùng thỏa thuận.")
    doc.add_paragraph("Nội dung tiền lương và thời hạn được hai bên ghi nhận.", style="List Bullet")
    body = doc.element.body
    inserted = doc.add_paragraph("Đoạn được thêm: công việc, tiền lương và thời giờ làm việc.")._p
    deleted = doc.add_paragraph("ĐOẠN ĐÃ XÓA phải không xuất hiện.")._p
    body.remove(inserted)
    body.remove(deleted)
    for kind, paragraph in (("ins", inserted), ("del", deleted)):
        wrapper = OxmlElement(f"w:{kind}")
        wrapper.append(paragraph)
        body.insert(len(body) - 1, wrapper)
    path = tmp_path / "accepted.docx"
    doc.save(path)
    text = extract(path, "docx").canonical_text
    assert "\n• Nội dung tiền lương" in text
    assert "Đoạn được thêm:" in text
    assert "ĐOẠN ĐÃ XÓA" not in text


def test_docx_limit_is_checked_on_canonical_code_points_and_bytes(tmp_path):
    doc = Document()
    doc.add_paragraph("Hợp đồng lao động và tiền lương của người lao động. " * 4 + "📄 a\u0301")
    path = tmp_path / "limit.docx"
    doc.save(path)
    canonical = extract(path, "docx").canonical_text
    assert "á" in canonical and "a\u0301" not in canonical
    assert extract(path, "docx", max_docx_chars=len(canonical)).char_count == len(canonical)
    with pytest.raises(ValidationReject) as rejected:
        extract(path, "docx", max_docx_chars=len(canonical) - 1)
    assert rejected.value.code == "DOCX_TEXT_LIMIT_EXCEEDED"
    with pytest.raises(ValidationReject) as rejected:
        extract(path, "docx", max_upload_bytes=path.stat().st_size - 1)
    assert rejected.value.code == "FILE_TOO_LARGE"


@pytest.mark.parametrize("filename,bytes_", [
    ("wrong.pdf", b"PK\x03\x04zip"),
    ("wrong.docx", b"%PDF-1.7\n"),
    ("corrupt.docx", b"PK\x03\x04not-a-valid-document"),
])
def test_docx_kind_and_corrupt_package_reject(tmp_path, filename, bytes_):
    path = tmp_path / filename
    path.write_bytes(bytes_)
    with pytest.raises(ValidationReject) as rejected:
        kind = detect_kind(path, path.name)
        extract(path, kind)
    assert rejected.value.code == "UNSUPPORTED_FILE_TYPE"


def test_empty_docx_rejects_without_partial_text(tmp_path):
    path = tmp_path / "empty.docx"
    Document().save(path)
    with pytest.raises(ValidationReject) as rejected:
        extract(path, "docx")
    assert rejected.value.code == "NO_EXTRACTABLE_TEXT"
