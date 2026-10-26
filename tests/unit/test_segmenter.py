"""C-01 (a): segment() — INV-02/03 (SKELETON §9), fallback paragraph, fixture, PII, giới hạn."""

from pathlib import Path

import pytest
from app.clause.segmenter import (
    LONG_CLAUSE_CHARS,
    SEGMENTATION_SCHEMA_VERSION,
    boundary_guard,
    segment,
)
from app.domain.errors import ValidationReject
from app.privacy.masker import mask
from app.privacy.pii_types import PiiSpan, PiiType

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "segmentation"


def load(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


def run(text: str):
    m = mask(text)
    return segment(text, m.masked_text, m.pii_spans)


def check_partition(text: str, result):
    """INV-02 + INV-03 + mọi ký tự khác khoảng trắng thuộc đúng một clause."""
    covered = [False] * len(text)
    prev_end = 0
    for c in result.clauses:
        assert text[c.start_char : c.end_char] == c.original_text  # INV-02
        assert c.original_text == c.original_text.strip()
        assert c.start_char >= prev_end and c.end_char > c.start_char  # INV-03
        prev_end = c.end_char
        for i in range(c.start_char, c.end_char):
            covered[i] = True
    for i, ch in enumerate(text):
        assert covered[i] or ch.isspace(), f"ký tự {i}={ch!r} không thuộc clause nào"
    ids = [c.clause_id for c in result.clauses]
    assert ids == [f"cl_{i + 1:04d}" for i in range(len(ids))]  # theo start_char tăng dần


# ---------------------------------------------- fixture nested_article_subclauses
def test_nested_article_subclauses_partition_and_hierarchy():
    text = load("nested_article_subclauses.txt")
    r = run(text)
    check_partition(text, r)
    by_num: dict = {}
    for c in r.clauses:  # số trùng ("1", "2" ở Điều 3): giữ bản đầu tiên = Điều
        by_num.setdefault(c.structure.number, c)

    # Preamble "HỢP ĐỒNG LAO ĐỘNG" (<40 ký tự, không có neighbor) vẫn là clause riêng, không level
    assert r.clauses[0].original_text == "HỢP ĐỒNG LAO ĐỘNG"
    assert r.clauses[0].structure.number is None

    # "Điều 2" chỉ gồm heading + lời dẫn trước 2.1 — KHÔNG bao trùm child (TDD §11.2)
    d2 = by_num["2"]
    assert d2.original_text.startswith("Điều 2. Tiền lương")
    assert d2.original_text.endswith("được thỏa thuận như sau:")
    assert "2.1" not in d2.original_text

    # 2.2 kết thúc trước a); a), b) là con của 2.2; 2.3 là anh em của 2.2
    assert by_num["2.2"].original_text == "2.2 Phụ cấp, gồm:"
    assert by_num["a"].structure.parent_clause_id == by_num["2.2"].clause_id
    assert by_num["b"].structure.level == by_num["a"].structure.level == 3
    assert by_num["2.3"].structure.parent_clause_id == d2.clause_id
    assert by_num["2.1"].structure.parent_clause_id == d2.clause_id

    # Điều 1 chỉ có heading, rồi tới 1.1 (parent chỉ gồm heading — hợp lệ)
    assert by_num["1"].original_text == "Điều 1. Công việc và địa điểm làm việc"

    # numbered "1." / "2." dưới Điều 3 là con của Điều 3
    d3 = by_num["3"]
    numbered = [c for c in r.clauses if c.structure.parent_clause_id == d3.clause_id]
    assert [c.structure.number for c in numbered] == ["1", "2"]
    assert all(c.structure.level == 2 for c in numbered)


def test_no_clause_contains_another_clause_span():
    text = load("nested_article_subclauses.txt")
    r = run(text)
    for a, b in zip(r.clauses, r.clauses[1:]):
        assert a.end_char <= b.start_char


# ------------------------------------------------------------------ fixture paragraph_fallback
def test_paragraph_fallback_without_headings():
    text = load("paragraph_fallback.txt")
    r = run(text)
    check_partition(text, r)
    assert all(
        c.structure.number is None and c.structure.parent_clause_id is None for c in r.clauses
    )
    assert all(c.structure.level == 1 for c in r.clauses)
    # "Lương" (<40 ký tự) được gộp với đoạn kế tiếp, không đứng riêng
    texts = [c.original_text for c in r.clauses]
    assert any(t.startswith("Lương\n\nHai bên") for t in texts)
    assert not any(t == "Lương" for t in texts)
    assert len(r.clauses) == 4


def test_no_blank_lines_splits_by_line_never_mid_line():
    text = (
        "Người lao động làm việc tám giờ mỗi ngày tại văn phòng công ty.\n"
        "Công ty trả lương vào ngày năm hằng tháng bằng chuyển khoản ngân hàng.\n"
        "Hợp đồng lập thành hai bản có giá trị pháp lý như nhau giữa các bên."
    )
    r = run(text)
    check_partition(text, r)
    assert [c.original_text for c in r.clauses] == text.split("\n")


def test_short_trailing_paragraph_merges_into_previous():
    long_p = "Người lao động làm việc tám giờ mỗi ngày tại văn phòng công ty."
    text = f"{long_p}\n\nKý tên"
    r = run(text)
    check_partition(text, r)
    assert len(r.clauses) == 1 and r.clauses[0].original_text == text


# ------------------------------------------------------------------ list tin cậy / false positive
def test_lists_false_positives_do_not_create_boundaries():
    text = load("lists_false_positives.txt")
    r = run(text)
    check_partition(text, r)
    nums = [c.structure.number for c in r.clauses]
    # "2.000.000 đồng" và "a)" lẻ nằm trong clause Điều 4; hai gạch đầu dòng thành 2 clause
    assert nums == ["4", "5", None, None]
    d4 = r.clauses[0].original_text
    assert "2.000.000" in d4 and "a) một mục lẻ" in d4
    assert all(c.structure.parent_clause_id == r.clauses[1].clause_id for c in r.clauses[2:])


# ------------------------------------------------------------------ PII / placeholder
def test_boundary_not_inside_placeholder_and_len_preserved():
    text = "Điều 1. Các bên\nEmail của người lao động: nguyenvana@example.com\nĐiều 2. Lương\n"
    m = mask(text)
    assert len(m.masked_text) == len(text)
    r = segment(text, m.masked_text, m.pii_spans)
    check_partition(text, r)
    for c in r.clauses:
        assert boundary_guard(c.start_char, m.pii_spans) and boundary_guard(c.end_char, m.pii_spans)
    # clause_text lấy từ canonical (còn email thật), không phải masked
    assert "nguyenvana@example.com" in r.clauses[0].original_text


def test_heading_inside_placeholder_is_not_a_boundary():
    # PII span giả: phủ trọn "Điều 2..." nên heading ở giữa placeholder phải bị bỏ.
    text = "Điều 1. A\nxx Điều 2. B yy\nĐiều 3. C\n"
    start = text.index("xx")
    span = PiiSpan(PiiType.LEGAL_ENTITY, start, start + len("xx Điều 2. B yy"))
    masked = text[:start] + "<ORG>" + "_" * (span.end - span.start - 5) + text[span.end :]
    r = segment(text, masked, [span])
    check_partition(text, r)
    assert [c.structure.number for c in r.clauses] == ["1", "3"]


def test_mismatched_length_is_rejected():
    with pytest.raises(ValueError, match="INV-01"):
        segment("abc", "ab", [])


# ------------------------------------------------------------------ giới hạn
def test_too_many_clauses_rejects():
    text = "\n".join(f"Điều {i}. Nội dung điều khoản số {i}" for i in range(1, 152))
    with pytest.raises(ValidationReject) as e:
        run(text)
    assert e.value.code == "TOO_MANY_CLAUSES"


def test_exactly_max_clauses_is_ok():
    text = "\n".join(f"Điều {i}. Nội dung điều khoản số {i}" for i in range(1, 151))
    r = run(text)
    assert len(r.clauses) == 150
    check_partition(text, r)


def test_long_clause_kept_whole_with_warning():
    body = "Điều 1. Dài\n" + ("Người lao động có nghĩa vụ tuân thủ nội quy. " * 120)
    assert len(body) > LONG_CLAUSE_CHARS
    r = run(body)
    assert len(r.clauses) == 1 and r.clauses[0].original_text == body.strip()
    assert r.warnings and "cl_0001" in r.warnings[0]


# ------------------------------------------------------------------ tổng quát
@pytest.mark.parametrize("text", ["", "   \n\n  ", "\n"])
def test_blank_input_gives_no_clauses(text):
    assert run(text).clauses == []


def test_unicode_offsets_are_code_points_not_utf16():
    # 😀 (U+1F600) ngoài BMP: 1 code point, 2 đơn vị UTF-16 — offset phải theo code point (INV-04).
    text = "Điều 1. Vui 😀 vẻ\nĐiều 2. Tiếp\n"
    r = run(text)
    check_partition(text, r)
    assert r.clauses[0].original_text == "Điều 1. Vui 😀 vẻ"
    assert r.clauses[1].start_char == len("Điều 1. Vui 😀 vẻ\n")


def test_nfc_decomposed_input_is_still_a_partition():
    import unicodedata

    text = unicodedata.normalize("NFC", "Điều 1. Công việc\nĐiều 2. Lương\n")
    r = run(text)
    check_partition(text, r)


def test_to_dict_matches_segmentation_v1_shape():
    text = load("nested_article_subclauses.txt")
    d = run(text).to_dict()
    assert d["schema_version"] == SEGMENTATION_SCHEMA_VERSION == "segmentation_v1"
    assert d["segmentation_version"] == "rules_v1.1" and d["offset_unit"] == "unicode_code_point"
    c0 = d["clauses"][0]
    assert set(c0) == {"clause_id", "original_text", "start_char", "end_char", "structure"}
    assert set(c0["structure"]) == {"level", "number", "parent_clause_id"}


def test_segmentation_is_deterministic():
    text = load("nested_article_subclauses.txt")
    assert run(text).to_dict() == run(text).to_dict()
