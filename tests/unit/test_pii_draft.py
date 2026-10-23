"""Spike C-09: PII masking draft. INV-02, không mask từ vai trò, không mask câu thường."""

import unicodedata
from pathlib import Path

import pytest
from privacy.pii_DRAFT import (
    PiiSpan,
    PiiType,
    adjust_boundary,
    boundary_guard,
    detect,
    mask,
    mask_value,
)

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "ai_pipeline" / "data" / "data" / "processed" / "raw_text"


def _spans(text):
    return [(s.type, text[s.start : s.end]) for s in detect(text)]


@pytest.mark.parametrize(
    "text",
    [
        "Người lao động có quyền được nghỉ hằng năm theo quy định.",
        "Công ty có quyền điều chuyển người lao động sang vị trí khác khi cần thiết, theo nhu cầu.",
        "Doanh nghiệp có nghĩa vụ đóng bảo hiểm xã hội đầy đủ cho người lao động.",
        "Người lao động: Có quyền được nghỉ phép năm.",
        "Hợp đồng có hiệu lực từ ngày 01/01/2026. Lương 10.000.000 đồng/tháng, 08 giờ/ngày.",
        "Địa điểm làm việc: Hà Nội. Nơi ở: do công ty bố trí.",
        "Công ty (sau đây gọi là Công ty) có trách nhiệm trả lương.",
        "Địa chỉ: ..........................................",
        "Ông/Bà: ……… Ngày sinh:………... Số CMND/CCCD :",
    ],
)
def test_ordinary_clause_text_and_blank_forms_are_untouched(text):
    assert detect(text) == []
    assert mask(text).masked_text == text


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Email: nguyenvana@gmail.com.", [(PiiType.EMAIL, "nguyenvana@gmail.com")]),
        ("SĐT 0912 345 678.", [(PiiType.PHONE, "0912 345 678")]),
        ("SĐT 0912.345.678", [(PiiType.PHONE, "0912.345.678")]),
        ("SĐT +84 912 345 678", [(PiiType.PHONE, "+84 912 345 678")]),
        ("SĐT 0912345678", [(PiiType.PHONE, "0912345678")]),
        ("CCCD: 079203012345", [(PiiType.NATIONAL_ID_OR_PASSPORT, "079203012345")]),
        ("CMND số 012345678", [(PiiType.NATIONAL_ID_OR_PASSPORT, "012345678")]),
        ("Hộ chiếu số: B1234567", [(PiiType.NATIONAL_ID_OR_PASSPORT, "B1234567")]),
        ("STK: 0123 4567 8901", [(PiiType.BANK_ACCOUNT, "0123 4567 8901")]),
        ("Sinh ngày 05 tháng 03 năm 1995", [(PiiType.DATE_OF_BIRTH, "05 tháng 03 năm 1995")]),
        ("Ngày sinh: 05/03/1995", [(PiiType.DATE_OF_BIRTH, "05/03/1995")]),
        ("Sinh năm: 1990", [(PiiType.DATE_OF_BIRTH, "1990")]),
        ("Họ và tên: NGUYỄN VĂN AN, sinh", [(PiiType.PERSON_NAME, "NGUYỄN VĂN AN")]),
        ("Ông Nguyễn Văn An", [(PiiType.PERSON_NAME, "Nguyễn Văn An")]),
        ("Ông/Bà: Trần Thị B\nNgười lao động", [(PiiType.PERSON_NAME, "Trần Thị B")]),
        ("Bà Nguyễn Thị Hoa Chức vụ: Kế toán trưởng", [(PiiType.PERSON_NAME, "Nguyễn Thị Hoa")]),
        ("Công ty TNHH ABC Việt Nam có trụ sở", [(PiiType.LEGAL_ENTITY, "ABC Việt Nam")]),
        ("MST: 0101234567", [(PiiType.LEGAL_ENTITY, "0101234567")]),
        (
            "Địa chỉ thường trú: 12 Nguyễn Trãi, phường Thượng Đình, quận Thanh Xuân, Hà Nội",
            [
                (
                    PiiType.RESIDENTIAL_ADDRESS,
                    "12 Nguyễn Trãi, phường Thượng Đình, quận Thanh Xuân, Hà Nội",
                )
            ],
        ),
    ],
)
def test_detects_value_only_not_anchor_or_role_word(text, expected):
    assert _spans(text) == expected


def test_mask_preserves_length_and_roles_and_leaves_no_overlap():
    text = "Đại diện bởi Ông Nguyễn Văn An (SĐT 0912 345 678), Người lao động có quyền nghỉ phép."
    r = mask(text)
    assert len(r.masked_text) == len(text)
    assert "Người lao động có quyền nghỉ phép." in r.masked_text
    spans = sorted(r.pii_spans, key=lambda s: s.start)
    assert all(a.end <= b.start for a, b in zip(spans, spans[1:]))
    assert "Nguyễn" not in r.masked_text and "0912" not in r.masked_text


def test_non_bmp_text_keeps_code_point_length():
    text = "😀 Họ và tên: Nguyễn Văn An 😀"
    assert len(mask(text).masked_text) == len(text)


def test_mask_value_length_rule():
    assert mask_value("nguyenvana@gmail.com", PiiType.EMAIL) == "<EMAIL>" + "_" * 13
    assert mask_value("An", PiiType.PERSON_NAME) == "NN"
    for pii_type in PiiType:
        for n in (1, 2, 5, 9, 30):
            assert len(mask_value("x" * n, pii_type)) == n


def test_non_nfc_input_is_rejected_not_silently_changed():
    decomposed = unicodedata.normalize("NFD", "Họ và tên: Nguyễn Văn An")
    with pytest.raises(ValueError):
        mask(decomposed)


def test_boundary_guard_and_adjust():
    spans = [PiiSpan(PiiType.PHONE, 10, 20)]
    assert boundary_guard(10, spans) and boundary_guard(20, spans) and boundary_guard(5, spans)
    assert not boundary_guard(15, spans)
    assert adjust_boundary(12, spans) == 10 and adjust_boundary(18, spans) == 20
    assert adjust_boundary(15, spans) == 10 and adjust_boundary(5, spans) == 5


@pytest.mark.parametrize("name", ["HDLD001", "HDLD003", "HDLD005"])
def test_blank_contract_templates_have_no_pii_spans(name):
    path = RAW / f"{name}.txt"
    if not path.exists():
        pytest.skip("data submodule chưa có")
    text = unicodedata.normalize("NFC", path.read_text(encoding="utf-8"))
    assert detect(text) == []
