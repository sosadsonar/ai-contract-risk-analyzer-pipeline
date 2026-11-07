import pytest

from ai_pipeline.evaluation.metrics import (
    evaluate_segmentation,
)
from ai_pipeline.evaluation.metrics.segmentation import CharacterSpan


def test_m1_greedy_iou_matching_returns_perfect_span_score():
    spans = (CharacterSpan(0, 8), CharacterSpan(10, 20))

    result = evaluate_segmentation(spans, spans)

    assert (result.tp, result.fp, result.fn) == (2, 0, 0)
    assert result.precision == result.recall == result.f1 == 1.0
    assert [(match.gold_index, match.predicted_index) for match in result.matches] == [(0, 0), (1, 1)]


def test_m1_requires_iou_at_least_point_eight_and_counts_unmatched_spans():
    gold = (CharacterSpan(0, 10), CharacterSpan(20, 30))
    predicted = (
        CharacterSpan(0, 8),
        CharacterSpan(20, 27),
        CharacterSpan(40, 45),
    )

    result = evaluate_segmentation(gold, predicted)

    assert result.iou_threshold == 0.8
    assert (result.tp, result.fp, result.fn) == (1, 2, 1)
    assert result.precision == pytest.approx(1 / 3)
    assert result.recall == 0.5
    assert result.f1 == pytest.approx(0.4)


def test_m1_scores_no_predictions_as_misses_without_perfect_empty_score():
    result = evaluate_segmentation((CharacterSpan(0, 5),), ())

    assert (result.tp, result.fp, result.fn) == (0, 0, 1)
    assert result.precision == result.recall == result.f1 == 0.0


def test_m1_rejects_both_empty_sets_instead_of_claiming_perfect_score():
    with pytest.raises(ValueError, match="requires at least one gold span"):
        evaluate_segmentation((), ())


@pytest.mark.parametrize(
    "span",
    [CharacterSpan(-1, 2), CharacterSpan(2, 2), CharacterSpan(4, 3), CharacterSpan(True, 3)],
)
def test_m1_rejects_invalid_character_spans(span):
    with pytest.raises(ValueError, match="spans must be non-empty non-negative integer ranges"):
        evaluate_segmentation((span,), (CharacterSpan(0, 2),))


def test_m1_uses_deterministic_index_tiebreak_for_equal_iou():
    gold = (CharacterSpan(0, 10), CharacterSpan(0, 10))
    predicted = (CharacterSpan(0, 10), CharacterSpan(0, 10))

    result = evaluate_segmentation(gold, predicted)

    assert [(match.gold_index, match.predicted_index) for match in result.matches] == [(0, 0), (1, 1)]
