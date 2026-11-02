"""C-01 (b): INV-02/03 khi CÓ PII — ranh giới không rơi vào placeholder; partition giữ nguyên.

Data D1 đã de-identify nên 6 hợp đồng thật cho 0 span PII → các test dùng văn bản tổng hợp và fuzz có seed.
"""

import random

from app.clause.segmenter import boundary_guard, segment
from app.privacy.masker import mask

PII = [
    "0912345678", "nguyen.van.a@example.com", "012345678901",
    "Số tài khoản: 0123456789012", "Ông Nguyễn Văn An", "MST 0312345678",
]
FRAGMENTS = [
    "Điều {n}. Tiền lương", "{n}.{n} Người lao động được trả lương", "{n}) Công việc", "a) Điều kiện",
    "- Ký tên:", "Hai bên thỏa thuận như sau:", "", "", "Người lao động: {pii}", "Điện thoại: {pii}",
    "{pii} {pii}", "{n}. {pii} là đại diện", "Email: {pii}.", "x", "Điều {n}", "HỢP ĐỒNG LAO ĐỘNG",
]


def make_text(rng: random.Random) -> str:
    lines = []
    for _ in range(rng.randint(1, 40)):
        frag = rng.choice(FRAGMENTS)
        lines.append(frag.format(n=rng.randint(1, 12), pii=rng.choice(PII)))
        if rng.random() < 0.15:
            lines.append("")
    return "\n".join(lines)


def assert_partition(text, result, spans):
    covered = [False] * len(text)
    prev_end = 0
    for c in result.clauses:
        assert text[c.start_char : c.end_char] == c.original_text  # INV-02
        assert c.start_char >= prev_end and c.end_char > c.start_char  # INV-03
        assert boundary_guard(c.start_char, spans) and boundary_guard(c.end_char, spans)
        prev_end = c.end_char
        for i in range(c.start_char, c.end_char):
            covered[i] = True
    for i, ch in enumerate(text):
        assert covered[i] or ch.isspace(), f"ký tự {i}={ch!r} rơi ra ngoài mọi clause"


def test_fuzz_partition_and_boundaries_with_pii():
    rng = random.Random(20261101)
    total_spans = 0
    for _ in range(400):
        text = make_text(rng)
        m = mask(text)
        assert len(m.masked_text) == len(text)  # INV-01
        total_spans += len(m.pii_spans)
        r = segment(text, m.masked_text, m.pii_spans, max_clauses=10_000)
        assert_partition(text, r, m.pii_spans)
    assert total_spans > 300  # fuzz thật sự có PII để thử ranh giới


def test_heading_inside_placeholder_is_dropped_not_moved():
    text = "Điều 1. Lương\nLương 10 triệu.\n0912345678 là số điện thoại\nĐiều 2. Nghỉ\nNghỉ phép."
    m = mask(text)
    assert m.pii_spans, "fixture phải có PII"
    r = segment(text, m.masked_text, m.pii_spans)
    assert_partition(text, r, m.pii_spans)
    assert all("0912345678" not in c.original_text or c.start_char <= text.index("0912345678") for c in r.clauses)


def test_pii_never_changes_clause_count_vs_unmasked_structure():
    plain = "Điều 1. A\nnội dung một\nĐiều 2. B\nnội dung hai\nĐiều 3. C\nnội dung ba"
    with_pii = plain.replace("nội dung một", "gọi 0912345678 hoặc nguyen.van.a@example.com")
    a = segment(plain, *[mask(plain).masked_text, mask(plain).pii_spans])
    m = mask(with_pii)
    b = segment(with_pii, m.masked_text, m.pii_spans)
    assert len(a.clauses) == len(b.clauses) == 3
    assert [c.structure.number for c in a.clauses] == [c.structure.number for c in b.clauses]


def test_span_text_of_clause_matches_canonical_even_with_non_bmp():
    text = "Điều 1. Công việc 😀\nLiên hệ 0912345678 😀😀\nĐiều 2. Lương\nTrả 5.000.000 đồng 🙂"
    m = mask(text)
    r = segment(text, m.masked_text, m.pii_spans)
    assert_partition(text, r, m.pii_spans)
    assert r.clauses[-1].end_char == len(text)  # offset theo code point, không phải UTF-16
