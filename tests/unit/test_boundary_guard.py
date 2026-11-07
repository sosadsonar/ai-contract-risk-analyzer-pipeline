"""X-20 (N1, W4): boundary_guard/adjust_boundary nằm ở clause/segmenter.py; test bằng span viết tay.

Không phụ thuộc masker/detector (N3) nên không phải chờ C-09.
"""

from app.clause.segmenter import adjust_boundary, boundary_guard, segment
from app.privacy.pii_types import PiiSpan, PiiType

SPANS = [PiiSpan(PiiType.PERSON_NAME, 10, 20), PiiSpan(PiiType.PHONE, 30, 31)]


def test_guard_false_only_strictly_inside_a_span():
    assert boundary_guard(10, SPANS) and boundary_guard(20, SPANS)  # mép span hợp lệ
    assert boundary_guard(0, SPANS) and boundary_guard(25, SPANS) and boundary_guard(40, SPANS)
    for pos in range(11, 20):
        assert not boundary_guard(pos, SPANS)


def test_guard_with_no_spans_and_one_char_span():
    assert boundary_guard(5, [])
    assert boundary_guard(30, SPANS) and boundary_guard(31, SPANS)  # span 1 ký tự: không có vị trí "bên trong"


def test_adjust_boundary_moves_to_nearest_edge_ties_to_start():
    assert adjust_boundary(12, SPANS) == 10
    assert adjust_boundary(18, SPANS) == 20
    assert adjust_boundary(15, SPANS) == 10  # hòa → đầu span
    assert adjust_boundary(25, SPANS) == 25 and adjust_boundary(10, SPANS) == 10


def test_masker_reexport_is_the_same_function():
    from app.privacy import masker

    assert masker.boundary_guard is boundary_guard
    assert masker.adjust_boundary is adjust_boundary


def test_segment_never_places_boundary_inside_handwritten_span():
    # "5.1 " bắt đầu ở 20..; đặt span phủ lên chính dòng marker để heading bị bỏ (không dời).
    text = "Điều 1. Công việc\n1.1 Làm việc tại Hà Nội\n1.2 Làm đủ giờ\nNguyen Van A ghi tên"
    start = text.index("1.2")
    spans = [PiiSpan(PiiType.PERSON_NAME, start + 1, start + 7)]  # span cắt ngang marker "1.2"
    masked = text  # chỉ kiểm ranh giới; nội dung placeholder không ảnh hưởng
    res = segment(text, masked, spans)
    for c in res.clauses:
        assert boundary_guard(c.start_char, spans) and boundary_guard(c.end_char, spans)
        assert text[c.start_char : c.end_char] == c.original_text
