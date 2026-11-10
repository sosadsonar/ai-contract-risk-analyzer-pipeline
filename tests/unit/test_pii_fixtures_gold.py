"""C-09 (b): detect()/mask() so với gold span của tests/fixtures/privacy + hồi quy các lỗi đã sửa.

Fixture là văn bản tổng hợp (không phải D1/T1). `known_misses` trong fixture là giới hạn đã biết của
regex: được miễn ở test hồi quy nhưng vẫn tính là sót trong số đo (`ai_pipeline/eval/eval_pii.py`).
"""

import json
from pathlib import Path

import pytest
from app.privacy.detector import detect
from app.privacy.masker import mask
from app.privacy.pii_types import PiiType

from ai_pipeline.eval.eval_pii import PRESERVE_THRESHOLD, evaluate_fixtures, load_fixtures

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "privacy"
CASES = load_fixtures(FIXTURE_DIR)


def _covered(start, end, spans):
    return sum(max(0, min(end, s.end) - max(start, s.start)) for s in spans) == end - start


@pytest.mark.parametrize("case", CASES, ids=[c["case_id"] for c in CASES])
def test_every_gold_span_is_fully_masked_except_known_misses(case):
    pred = detect(case["canonical_text"])
    known = {(m["start"], m["end"]) for m in case.get("known_misses", [])}
    for gold in case["pii_spans"]:
        if (gold["start"], gold["end"]) in known:
            continue
        assert _covered(gold["start"], gold["end"], pred), (case["case_id"], gold["text"])
        assert any(
            s.type.value == gold["type"] and s.start <= gold["start"] and gold["end"] <= s.end for s in pred
        ), f"đúng vị trí nhưng sai loại: {gold['text']!r}"


@pytest.mark.parametrize("case", CASES, ids=[c["case_id"] for c in CASES])
def test_preserve_spans_are_never_touched(case):
    pred = detect(case["canonical_text"])
    for keep in case["preserve_spans"]:
        assert not any(s.start < keep["end"] and keep["start"] < s.end for s in pred), keep["text"]
        masked = mask(case["canonical_text"]).masked_text
        assert masked[keep["start"] : keep["end"]] == keep["text"]


def test_known_misses_are_listed_in_gold_and_still_missed():
    """Giới hạn đã biết phải còn ghi trong fixture; khi detector sửa được thì chuyển sang gold thường."""
    for case in CASES:
        pred = detect(case["canonical_text"])
        for m in case.get("known_misses", []):
            assert not _covered(m["start"], m["end"], pred), f"{m['text']!r} đã bắt được: bỏ khỏi known_misses"


def test_measured_thresholds_regression():
    fx = evaluate_fixtures(CASES)
    for name, g in fx["groups"].items():
        assert g["recall"] is not None and g["recall"] >= g["threshold"], (name, g)
    assert fx["preserve"]["rate"] >= PRESERVE_THRESHOLD
    assert fx["false_positive"] == []


def _types(text):
    return [(s.type, text[s.start : s.end]) for s in detect(text)]


@pytest.mark.parametrize(
    "text, expected",
    [
        ("MST: 0312345678", [(PiiType.TAX_ID, "0312345678")]),
        ("Mã số thuế: 0312345678-001", [(PiiType.TAX_ID, "0312345678-001")]),
        ("MST 0801234567", [(PiiType.TAX_ID, "0801234567")]),
        ("SĐT 0312345678", [(PiiType.PHONE, "0312345678")]),
        ("Mã số thuế: 0312345678, SĐT 0312345679", [
            (PiiType.TAX_ID, "0312345678"), (PiiType.PHONE, "0312345679")]),
    ],
)
def test_tax_code_is_not_mistaken_for_phone(text, expected):
    assert _types(text) == expected


@pytest.mark.parametrize(
    "text, phone",
    [
        ("Điện thoại bàn: 024 3825 1234", "024 3825 1234"),
        ("ĐT 024.38251234", "024.38251234"),
        ("ĐT: 02438251234", "02438251234"),
        ("Điện thoại: (024) 3825 1234", "(024) 3825 1234"),
        ("SĐT +84 24 3825 1234", "+84 24 3825 1234"),
    ],
)
def test_landline_phone_numbers(text, phone):
    assert _types(text) == [(PiiType.PHONE, phone)]


@pytest.mark.parametrize(
    "text",
    ["CCCD: 022203012345", "Lương 020.000.000.000 đồng", "Số: 02/2026/HĐLĐ", "Ngày 02/12/2026 ký hợp đồng"],
)
def test_landline_pattern_does_not_swallow_ids_money_or_dates(text):
    assert PiiType.PHONE not in {t for t, _ in _types(text)}


@pytest.mark.parametrize(
    "text, name",
    [
        ("Đại diện: Ông Lê Quốc Huy, Tổng giám đốc", "Lê Quốc Huy"),
        ("Họ và tên: Trần Văn Điện", "Trần Văn Điện"),
        ("Ông Nguyễn Văn Năm sinh ngày 5", "Nguyễn Văn Năm"),
        ("Họ và tên: Trần Văn An Quốc tịch: Việt Nam", "Trần Văn An"),
        ("Bà Nguyễn Thị Hoa Chức vụ: Kế toán trưởng", "Nguyễn Thị Hoa"),
        ("Họ và tên: Trần Văn An Số CMND: 012345678", "Trần Văn An"),
        ("Họ và tên: Trần Văn An Điện thoại: 0912345678", "Trần Văn An"),
        ("Họ và tên: Trần Văn An Năm sinh: 1990", "Trần Văn An"),
    ],
)
def test_name_is_not_truncated_at_name_like_words_but_stops_at_next_label(text, name):
    found = [t for ty, t in _types(text) if ty is PiiType.PERSON_NAME]
    assert found == [name]


def test_fixture_files_are_valid_and_carry_gold_text():
    for p in FIXTURE_DIR.glob("case_*.json"):
        obj = json.loads(p.read_text(encoding="utf-8"))
        for g in obj["pii_spans"]:
            assert obj["canonical_text"][g["start"] : g["end"]] == g["text"], (p.name, g)
        for g in obj["preserve_spans"]:
            assert obj["canonical_text"][g["start"] : g["end"]] == g["text"], (p.name, g)
