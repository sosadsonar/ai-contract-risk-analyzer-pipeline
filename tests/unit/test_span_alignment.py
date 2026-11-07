"""Shared M7 span-alignment behavior."""

import pytest

from ai_pipeline.evaluation.metrics.alignment import greedy_align_spans, span_iou


def test_inclusive_half_threshold_and_one_to_one_matching():
    assert greedy_align_spans([(0, 10), (10, 20)], [(0, 20), (0, 9)]) == [(0, 1), (1, 0)]


def test_heading_plus_body_below_threshold_stays_unmatched():
    assert greedy_align_spans([(10, 20)], [(0, 30)]) == []


def test_tied_scores_use_stable_indices():
    assert greedy_align_spans([(0, 10), (0, 10)], [(0, 10), (0, 10)]) == [(0, 0), (1, 1)]


def test_unicode_offsets_count_codepoints_and_reject_invalid_spans():
    text = "A😀B"
    assert text[1:2] == "😀"
    assert span_iou((1, 2), (1, 2)) == 1.0
    with pytest.raises(ValueError):
        span_iou((1, 1), (1, 2))
