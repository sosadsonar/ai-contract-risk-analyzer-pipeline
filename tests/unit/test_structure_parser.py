"""C-02: structure_parser — 5 pattern, level/parent, độ tin cậy của list, boundary_guard."""

from app.clause.structure_parser import (
    ARTICLE,
    DASH,
    DECIMAL,
    LETTERED,
    NUMBERED,
    parse_structure,
)


def kinds(text, **kw):
    return [(m.kind, m.number) for m in parse_structure(text, **kw)]


def test_article_and_decimal_children():
    text = "Điều 5. Lương\n5.1 Lương cơ bản\n5.2 Phụ cấp\nĐiều 6: Nghỉ phép\n"
    marks = parse_structure(text)
    assert [(m.kind, m.number, m.level) for m in marks] == [
        (ARTICLE, "5", 1),
        (DECIMAL, "5.1", 2),
        (DECIMAL, "5.2", 2),
        (ARTICLE, "6", 1),
    ]
    assert [m.parent_index for m in marks] == [None, 0, 0, None]


def test_decimal_depth_three_levels():
    text = "Điều 1. A\n1.1 B\n1.1.1 C\n1.1.2 D\n1.2 E\n"
    marks = parse_structure(text)
    assert [m.level for m in marks] == [1, 2, 3, 3, 2]
    assert marks[2].parent_index == 1 and marks[4].parent_index == 0


def test_numbered_and_lettered_under_article_are_nested():
    text = "Điều 3. X\n1. một\n2. hai\na) con a\nb) con b\n"
    marks = parse_structure(text)
    assert [(m.kind, m.level) for m in marks] == [
        (ARTICLE, 1),
        (NUMBERED, 2),
        (NUMBERED, 2),
        (LETTERED, 3),
        (LETTERED, 3),
    ]
    assert marks[3].parent_index == 2  # a) thuộc "2."


def test_lone_numbered_lettered_and_dash_are_not_boundaries():
    text = "Điều 1. X\n1. chỉ một mục\nĐiều 2. Y\na) lẻ\n- lẻ\n"
    assert kinds(text) == [(ARTICLE, "1"), (ARTICLE, "2")]


def test_dash_list_needs_two_siblings():
    text = "Điều 1. X\n- một\n- hai\n"
    assert kinds(text) == [(ARTICLE, "1"), (DASH, None), (DASH, None)]


def test_numbered_must_start_at_one_and_be_consecutive():
    assert kinds("Điều 1. X\n3. ba\n4. bốn\n") == [(ARTICLE, "1")]
    assert kinds("Điều 1. X\n1. một\n3. ba\n") == [(ARTICLE, "1")]


def test_lettered_sequence_accepts_vietnamese_d_stroke():
    text = "Điều 1. X\na) a\nb) b\nc) c\nd) d\nđ) đ\ne) e\n"
    marks = parse_structure(text)
    assert [m.number for m in marks if m.kind == LETTERED] == ["a", "b", "c", "d", "đ", "e"]


def test_thousands_separator_is_not_a_decimal_heading():
    text = "Điều 1. Lương\n2.000.000 đồng mỗi tháng\n1.500 đồng\n"
    assert kinds(text) == [(ARTICLE, "1")]


def test_inline_article_reference_is_not_a_heading():
    text = "Điều 1. X\nTheo quy định tại Điều 26 của Bộ luật Lao động thì...\n"
    assert kinds(text) == [(ARTICLE, "1")]


def test_leading_whitespace_is_ignored_and_start_points_at_first_char():
    text = "  Điều 1. A\n\t1.1 B\n"
    marks = parse_structure(text)
    assert [text[m.start] for m in marks] == ["Đ", "1"]


def test_boundary_guard_drops_heading_inside_placeholder():
    text = "Điều 1. A\nĐiều 2. B\n"
    second = text.index("Điều 2")
    marks = parse_structure(text, boundary_guard=lambda pos: pos != second)
    assert [m.number for m in marks] == ["1"]


def test_no_headings():
    assert parse_structure("Chỉ là một đoạn văn bình thường.\nDòng hai.") == []
    assert parse_structure("") == []


def test_dropping_weak_group_reparents_children():
    # "1." lẻ bị bỏ ⇒ "a) b)" phải gắn lại vào Điều 1, không treo vào mark đã bị bỏ.
    text = "Điều 1. X\n1. lẻ\na) một\nb) hai\n"
    marks = parse_structure(text)
    assert [(m.kind, m.level, m.parent_index) for m in marks] == [
        (ARTICLE, 1, None),
        (LETTERED, 2, 0),
        (LETTERED, 2, 0),
    ]
