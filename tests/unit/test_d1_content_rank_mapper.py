"""Content-rank rebasing for a reviewed D1 coordinate candidate."""

import pytest

from scripts.build_d1_pipeline_canonical_candidate import ContentRankMapper


def test_repeated_tail_does_not_anchor_to_the_wrong_occurrence():
    source = "Điều 1\nA\n\n\nB\nKý tên\n\n\nKý tên"
    target = "Điều 1\nA\n\n\nB\nKý tên\nKý tên"
    mapper = ContentRankMapper(source, target)
    start = source.rindex("Ký tên")
    new_start, new_end = mapper.span(start, len(source))
    assert target[new_start:new_end] == "Ký tên"
    assert new_end == len(target)


def test_unicode_codepoints_and_whitespace_only_boundary_changes():
    mapper = ContentRankMapper("A\u00a0😀\tB", "A 😀 B")
    assert mapper.span(2, 3) == (2, 3)
    assert mapper.span(0, 5) == (0, 5)


def test_changed_content_or_empty_content_span_fails_closed():
    with pytest.raises(ValueError, match="changed non-whitespace"):
        ContentRankMapper("A B", "A C")
    mapper = ContentRankMapper("A  B", "A B")
    with pytest.raises(ValueError, match="no content-bearing"):
        mapper.span(1, 3)
