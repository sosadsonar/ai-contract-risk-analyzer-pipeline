"""Spike C-09: PII masking draft. INV-01, không mask từ vai trò, không mask câu thường."""

import unicodedata
from pathlib import Path

import pytest
from app.privacy.detector import detect
from app.privacy.masker import adjust_boundary, boundary_guard, mask, mask_value
from app.privacy.pii_types import PiiSpan, PiiType

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "ai_pipeline" / "data" / "data" / "processed" / "raw_text"


_LONG_FILLER = ("Điều khoản chung về công việc và thời gian làm việc theo quy định của pháp luật. " * 12)


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
        ("MST: 0101234567", [(PiiType.TAX_ID, "0101234567")]),
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


@pytest.mark.parametrize(
    "text",
    ["Đại diện: Phó Giám đốc", "Họ và tên: Kế toán trưởng", "Đại diện: Tổng giám đốc"],
)
def test_job_title_after_role_anchor_is_not_masked(text):
    assert _spans(text) == []


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Cấp ngày: 12/03/2019\nTại: Cục Cảnh sát QLHC", [(PiiType.ID_ISSUE, "12/03/2019"), (PiiType.ID_ISSUE, "Cục Cảnh sát QLHC")]),
        ("nơi cấp: Công an tỉnh Nghệ An", [(PiiType.ID_ISSUE, "Công an tỉnh Nghệ An")]),
        ("cấp ngày 5 tháng 7 năm 2020 tại Hà Nội", [(PiiType.ID_ISSUE, "5 tháng 7 năm 2020"), (PiiType.ID_ISSUE, "Hà Nội")]),
        ("Cấp ngày: ………", []),
        ("Địa chỉ trụ sở chính: 25 Lê Lợi, Quận 1, TP. HCM", [(PiiType.BUSINESS_ADDRESS, "25 Lê Lợi, Quận 1, TP. HCM")]),
        ("Địa chỉ: Hà Nội", []),
        ("Địa chỉ: Thành phố Hồ Chí Minh", []),
        ("Mã số thuế: ……", []),
        ("Mã số thuế : 0312345678001", [(PiiType.TAX_ID, "0312345678001")]),
        ("Công ty TNHH có quyền", []),
        ("Công ty TNHH Sao Mai Việt Nam có trụ sở", [(PiiType.LEGAL_ENTITY, "Sao Mai Việt Nam")]),
        ("ký ngày 01/01/2026", []),
        ("làm việc tại Công ty", []),
    ],
)
def test_x17_value_only_and_blank_forms_untouched(text, expected):
    assert _spans(text) == expected


def test_plain_address_anchor_follows_nearest_party_heading():
    a = "Bên A (Người sử dụng lao động): X\nĐịa chỉ: 25 Lê Lợi, Quận 1, TP. HCM"
    b = "Bên B (Người lao động): Y\nĐịa chỉ: 25 Lê Lợi, Quận 1, TP. HCM"
    assert _spans(a) == [(PiiType.BUSINESS_ADDRESS, "25 Lê Lợi, Quận 1, TP. HCM")]
    assert _spans(b) == [(PiiType.RESIDENTIAL_ADDRESS, "25 Lê Lợi, Quận 1, TP. HCM")]


def test_signature_only_in_last_fifth_and_roles_not_masked():
    body = _LONG_FILLER + "\n\nNGƯỜI LAO ĐỘNG    NGƯỜI SỬ DỤNG LAO ĐỘNG\n(Ký, ghi rõ họ tên)    (Ký tên, đóng dấu)\nNguyễn Văn An    Trần Thị Bình\n"
    assert [(s.type, body[s.start:s.end]) for s in detect(body)] == [
        (PiiType.SIGNATURE, "Nguyễn Văn An"), (PiiType.SIGNATURE, "Trần Thị Bình")]
    early = "(Ký, ghi rõ họ tên)\nNguyễn Văn An\n" + _LONG_FILLER
    assert detect(early) == []


def test_x17_masking_is_length_preserving_and_idempotent():
    text = _LONG_FILLER + "\nĐịa chỉ trụ sở: 25 Lê Lợi, Quận 1\nCấp ngày: 12/03/2019\n(Ký, ghi rõ họ tên)\nNguyễn Văn An    Trần Thị Bình\n"
    once = mask(text)
    assert len(once.masked_text) == len(text)
    assert detect(once.masked_text) == []


def test_signature_wins_over_person_name_on_the_same_span():
    text = _LONG_FILLER + "\n\nKý tên: Nguyễn Văn An\n"
    spans = detect(text)
    covering = [s for s in spans if s.start <= text.index("Nguyễn") < s.end]
    assert [s.type for s in covering] == [PiiType.SIGNATURE]


def test_mst_and_phone_on_one_line_are_two_spans():
    types = [s.type for s in detect("MST: 0312345678 SĐT: 0912345678")]
    assert PiiType.TAX_ID in types and PiiType.PHONE in types


def test_address_is_limited_to_the_anchor_line():
    text = "Địa chỉ trụ sở: 25 Lê Lợi, Quận 1\nGhi chú: Liên hệ phòng nhân sự."
    spans = [(s.type, text[s.start:s.end]) for s in detect(text)]
    assert spans == [(PiiType.BUSINESS_ADDRESS, "25 Lê Lợi, Quận 1")]


def test_text_outside_spans_is_unchanged_by_masking():
    text = "Mã số thuế: 0312345678, địa chỉ thường trú: 5 ngõ 7, Hà Nội. Giám đốc ký.\n" + _LONG_FILLER
    result = mask(text)
    assert len(result.masked_text) == len(text)
    spans = sorted((s.start, s.end) for s in result.pii_spans)
    for i, ch in enumerate(text):
        if not any(a <= i < b for a, b in spans):
            assert result.masked_text[i] == ch, i


def test_signature_takes_at_most_four_non_empty_lines_after_label():
    names = ["Anh Văn Một", "Bảo Văn Hai", "Chi Văn Ba", "Dũng Văn Bốn", "Hải Văn Năm"]
    text = _LONG_FILLER + "\n(Ký, ghi rõ họ tên)\n" + "\n".join(names) + "\n"
    sig = [text[s.start:s.end] for s in detect(text) if s.type is PiiType.SIGNATURE]
    assert sig == names[:4]


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
