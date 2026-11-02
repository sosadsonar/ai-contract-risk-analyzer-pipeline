"""Contract-facing PDF extraction regressions (C-08a, FR-05/07/08)."""

import json
import unicodedata
from pathlib import Path

import pymupdf as fitz
import pytest
from app.core.enums import Role
from app.document.canonicalizer import canonicalize
from app.document.extractor import detect_kind, extract
from app.document.quality import run_quality_gates
from app.domain.errors import ValidationReject
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]


def _pdf(path, lines_by_page):
    doc = fitz.open()
    for lines in lines_by_page:
        page = doc.new_page(width=595, height=842)
        for x, y, text in lines:
            page.insert_text((x, y), text, fontsize=11)
    doc.save(path)
    doc.close()
    return path


def _long_line(label):
    return f"{label}: Employer and employee agree on working hours, salary and contract term for the next twelve months."  # noqa: E501


def test_canonicalization_preserves_structural_newlines_nfc_and_code_points():
    text = canonicalize(["Die\u0302\u0300u 1.\r\nNo\u0302\u0323i dung\u00a0  \r\n", "📄\t  \n\n\n\nĐiều 2."])
    assert text == "Diều 1.\nNội dung\n📄\n\n\nĐiều 2."
    assert unicodedata.is_normalized("NFC", text)
    assert len("📄") == 1


def test_pdf_extraction_has_stable_two_column_reading_order_and_schema(tmp_path):
    path = _pdf(tmp_path / "columns.pdf", [[
        (50, 110, "LEFT_FIRST: Salary and duties under contract."),
        (50, 140, "LEFT_SECOND: Work and rest under contract."),
        (325, 110, "RIGHT_FIRST: Employee rights under contract."),
        (325, 140, "RIGHT_SECOND: Employer duties under contract."),
    ]])
    kind = detect_kind(path, path.name)
    first = extract(path, kind)
    assert first == extract(path, kind)
    text = first.canonical_text
    assert text.index("LEFT_FIRST") < text.index("LEFT_SECOND") < text.index("RIGHT_FIRST") < text.index("RIGHT_SECOND")
    assert first.char_count == len(text) and first.page_count == 1
    schema = json.loads((ROOT / "ai_pipeline/schemas/extraction_v1.json").read_text(encoding="utf-8"))
    assert set(schema["properties"]["role"]["enum"]) == {role.value for role in Role}
    assert not list(Draft202012Validator(schema).iter_errors(first.to_artifact(path.name, Role.EMPLOYEE)))


def test_repeated_marginal_lines_and_page_numbers_are_removed_without_body_loss(tmp_path):
    pages = []
    for number in range(1, 4):
        pages.append([
            (45, 23, "CONTRACT COPY" if number <= 2 else "UNIQUE HEADER"),
            (45, 180, _long_line(f"BODY_{number}")),
            (45, 205, _long_line("ACTUAL CONTRACT CONTENT")),
            (45, 823, "CONTRACT COPY"),
            (295, 830, str(number)),
        ])
    result = extract(_pdf(tmp_path / "headers.pdf", pages), "pdf")
    assert "CONTRACT COPY" not in result.canonical_text
    assert all(f"BODY_{number}" in result.canonical_text for number in range(1, 4))
    assert "ACTUAL CONTRACT CONTENT" in result.canonical_text
    assert "UNIQUE HEADER" in result.canonical_text


def test_single_page_margin_text_is_preserved(tmp_path):
    path = _pdf(tmp_path / "one.pdf", [[(45, 23, "UNIQUE CONTRACT HEADER"),
                                         (45, 180, _long_line("BODY")),
                                         (45, 215, _long_line("SECOND"))]])
    assert "UNIQUE CONTRACT HEADER" in extract(path, "pdf").canonical_text


def test_pdf_table_rows_are_flattened_once(tmp_path):
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    for y in (100, 130, 160):
        page.draw_line((50, y), (450, y))
    for x in (50, 250, 450):
        page.draw_line((x, 100), (x, 160))
    for x, y, text in ((62, 120, "ITEM"), (262, 120, "VALUE"),
                       (62, 150, "Salary"), (262, 150, "12000000")):
        page.insert_text((x, y), text)
    page.insert_text((50, 220), _long_line("CONTRACT"))
    page.insert_text((50, 250), _long_line("CONTENT"))
    path = tmp_path / "table.pdf"
    doc.save(path)
    doc.close()
    text = extract(path, "pdf").canonical_text
    assert "ITEM | VALUE" in text and "Salary | 12000000" in text
    assert text.count("Salary") == 1


@pytest.mark.parametrize("name, payload", [
    ("file.pdf", b"PK\x03\x04not-a-pdf"),
    ("file.doc", b"%PDF-not-an-allowed-extension"),
])
def test_extension_and_magic_must_both_match(tmp_path, name, payload):
    path = tmp_path / name
    path.write_bytes(payload)
    with pytest.raises(ValidationReject, match="UNSUPPORTED_FILE_TYPE"):
        detect_kind(path, name)


def test_pdf_page_and_byte_caps_reject_before_text_extraction(tmp_path):
    path = _pdf(tmp_path / "oversize-pages.pdf", [[] for _ in range(31)])
    with pytest.raises(ValidationReject, match="PDF_PAGE_LIMIT_EXCEEDED"):
        extract(path, "pdf")
    with pytest.raises(ValidationReject, match="FILE_TOO_LARGE"):
        extract(path, "pdf", max_upload_bytes=path.stat().st_size - 1)


def test_scanned_and_corrupt_pdf_reject_without_partial_text(tmp_path):
    scanned = _pdf(tmp_path / "scanned.pdf", [[]])
    with pytest.raises(ValidationReject, match="NO_EXTRACTABLE_TEXT"):
        extract(scanned, "pdf")
    corrupted = tmp_path / "corrupted.pdf"
    corrupted.write_bytes(b"%PDF-1.7\nthis is not a PDF")
    with pytest.raises(ValidationReject, match="NO_EXTRACTABLE_TEXT"):
        extract(corrupted, detect_kind(corrupted, corrupted.name))


def test_pdf_with_legacy_extraction_glyphs_is_rejected(tmp_path):
    garbled = "Hîp ®ång lµm viÖc ®· tháa thuËn theo ®iÒu kho¶n ®­îc ghi nhËn."
    path = _pdf(tmp_path / "legacy.pdf", [[
        (50, 100 + index * 32, garbled) for index in range(5)
    ]])
    with pytest.raises(ValidationReject, match="UNSUPPORTED_TEXT_ENCODING"):
        extract(path, "pdf")


def test_legacy_font_fixture_and_quality_thresholds():
    legacy = (ROOT / "tests/fixtures/extraction/legacy_tcvn3.txt").read_text(encoding="utf-8")
    with pytest.raises(ValidationReject, match="UNSUPPORTED_TEXT_ENCODING"):
        run_quality_gates(legacy)
    valid = ("Hợp đồng lao động: người lao động và người sử dụng lao động thỏa thuận về "
             "công việc và tiền lương. ") * 4
    run_quality_gates(valid + "Ký hiệu đăng ký ® xuất hiện một lần.")
    with pytest.raises(ValidationReject, match="UNSUPPORTED_TEXT_ENCODING"):
        run_quality_gates("x" * 200 + "\ufffd" * 6)
    with pytest.raises(ValidationReject, match="UNSUPPORTED_TEXT_ENCODING"):
        run_quality_gates("Hợp đồng lao động " * 20 + "\x01")
    with pytest.raises(ValidationReject, match="UNSUPPORTED_TEXT_ENCODING"):
        run_quality_gates("x" * 100 + "\u200b" * 10)
    with pytest.raises(ValidationReject, match="NO_EXTRACTABLE_TEXT"):
        run_quality_gates("ảnh không có text")
