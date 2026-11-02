"""INV-01 (TDD §19.2): len(masked_text) == len(canonical_text), tính theo code point (C-09 a)."""

import dataclasses
import json
import random
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pytest
from app.privacy.masker import mask, mask_value
from app.privacy.pii_types import TYPE_SHORT_CODE, TYPE_TAG, MaskResult, PiiSpan, PiiType

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "privacy"


@dataclass(frozen=True)
class PrivacyCase:
    case_id: str
    canonical_text: str
    pii_spans: list[dict]  # {"type": str, "start": int, "end": int, "text": str}
    preserve_spans: list[dict]  # {"start": int, "end": int, "text": str}


def load_privacy_cases() -> list[PrivacyCase]:
    """Đọc mọi FIXTURE_DIR/case_*.json (utf-8), sort theo tên file. Fail nếu không có file nào."""
    paths = sorted(FIXTURE_DIR.glob("case_*.json"), key=lambda p: p.name)
    assert paths, f"không có fixture trong {FIXTURE_DIR}"
    cases = []
    for p in paths:
        obj = json.loads(p.read_text(encoding="utf-8"))
        assert obj["schema_version"] == "privacy_fixture_v1", p
        cases.append(
            PrivacyCase(
                obj["case_id"], obj["canonical_text"], obj["pii_spans"], obj["preserve_spans"]
            )
        )
    return cases


CASES = load_privacy_cases()
CASE_IDS = [c.case_id for c in CASES]


def _case(case_id: str) -> PrivacyCase:
    return next(c for c in CASES if c.case_id == case_id)


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_mask_length_equal_on_fixtures(case):
    assert len(mask(case.canonical_text).masked_text) == len(case.canonical_text)


def test_length_is_code_points_not_utf16():
    text = _case("case_002").canonical_text
    assert any(ord(ch) > 0xFFFF for ch in text)
    assert len(text.encode("utf-16-le")) // 2 > len(text)
    assert len(mask(text).masked_text) == len(text)


def test_mask_value_length_all_types_and_sizes():
    for t in PiiType:
        for n in range(1, 81):
            for s in ("x" * n, "😀" * n):
                assert len(mask_value(s, t)) == n, (t, n)


def test_mask_value_short_code_vs_tag():
    for t in PiiType:
        tag = TYPE_TAG[t]
        for n in (len(tag) - 1, len(tag), len(tag) + 1):
            out = mask_value("x" * n, t)
            if n < len(tag):
                assert out == TYPE_SHORT_CODE[t] * n, (t, n)
            else:
                assert out.startswith(tag), (t, n, out)
                assert set(out[len(tag):]) <= {"_"}, (t, n, out)


FRAGMENTS = [
    "Họ và tên: Nguyễn Văn An",
    "SĐT 0912 345 678",
    "Email: an.nguyen@example.com",
    "CCCD: 079203012345",
    "STK: 0123 4567 8901",
    "Ngày sinh: 05/03/1995",
    "Địa chỉ: 12 đường Láng, quận Đống Đa, Hà Nội",
    "Công ty TNHH Sao Mai có trụ sở",
    "MST: 0101234567",
    "Người lao động có quyền nghỉ phép.",
    "Lương 10.000.000 đồng/tháng",
    "😀",
    "𝐀",
    "\n",
    " ",
    "Điều 5.",
    "Ông Trần Văn Bình",
]


def test_mask_random_text_fixed_seed():
    rng = random.Random(20261024)
    for _ in range(300):
        parts = (rng.choice(FRAGMENTS) for _ in range(rng.randint(1, 12)))
        s = unicodedata.normalize("NFC", "".join(parts))
        assert len(mask(s).masked_text) == len(s), repr(s)


def test_length_guard_raises_runtime_error(monkeypatch):
    monkeypatch.setattr("app.privacy.masker.mask_value", lambda text, pii_type: "x")
    with pytest.raises(RuntimeError):
        mask(_case("case_001").canonical_text)


def test_mask_result_has_no_reverse_mapping():
    assert {f.name for f in dataclasses.fields(MaskResult)} == {"masked_text", "pii_spans"}
    assert {f.name for f in dataclasses.fields(PiiSpan)} == {"type", "start", "end"}


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_pii_spans_sorted_nonoverlapping_in_bounds(case):
    spans = mask(case.canonical_text).pii_spans
    n = len(case.canonical_text)
    for s in spans:
        assert 0 <= s.start < s.end <= n
    assert [s.start for s in spans] == sorted(s.start for s in spans)
    for a, b in zip(spans, spans[1:]):
        assert a.end <= b.start


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_text_outside_spans_unchanged(case):
    result = mask(case.canonical_text)
    covered = set()
    for s in result.pii_spans:
        covered.update(range(s.start, s.end))
    for i, ch in enumerate(case.canonical_text):
        if i not in covered:
            assert result.masked_text[i] == ch, i


def test_empty_text():
    result = mask("")
    assert result.masked_text == ""
    assert result.pii_spans == []
    for t in PiiType:
        assert mask_value("", t) == ""


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_fixture_gold_offsets_self_consistent(case):
    assert unicodedata.normalize("NFC", case.canonical_text) == case.canonical_text
    for d in case.pii_spans:
        assert case.canonical_text[d["start"]:d["end"]] == d["text"]
        assert d["type"] in {t.value for t in PiiType}
    for d in case.preserve_spans:
        assert case.canonical_text[d["start"]:d["end"]] == d["text"]
    if case.case_id == "case_003":
        assert case.pii_spans == []
