"""Shared M7 span-alignment behavior."""

import pytest

from ai_pipeline.evaluation.metrics.alignment import diagnose_span_alignment, greedy_align_spans, span_iou


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


def test_dual_mode_reports_containment_without_changing_one_to_one_matches():
    result = diagnose_span_alignment([(10, 20), (20, 30)], [(0, 40)])
    assert result["greedy_iou_pairs"] == []
    assert result["containment_pairs"] == [(0, 0), (1, 0)]


def test_dual_mode_filters_outside_scope_blank_and_heading_only_predictions():
    text = "Mở đầu\nĐiều 1\nNội dung điều khoản\n\nKý tên"
    body_start = text.index("Nội dung")
    body_end = body_start + len("Nội dung điều khoản")
    spans = [(0, 6), (7, 13), (body_start, body_end), (body_end + 1, body_end + 2), (len(text) - 6, len(text))]
    result = diagnose_span_alignment(
        [(body_start, body_end)], spans, text=text, clause_scope=(7, body_end + 2)
    )
    assert result["greedy_iou_pairs"] == [(0, 2)]
    assert result["containment_pairs"] == [(0, 2)]
    assert result["excluded_prediction_indices"] == {
        0: "outside_clause_scope",
        1: "heading_only",
        3: "blank_text",
        4: "outside_clause_scope",
    }


def test_containment_includes_exact_0_8_and_rejects_invalid_threshold():
    assert diagnose_span_alignment([(0, 10)], [(0, 8)])["containment_pairs"] == [(0, 0)]
    with pytest.raises(ValueError):
        diagnose_span_alignment([(0, 10)], [(0, 8)], containment_threshold=0)
