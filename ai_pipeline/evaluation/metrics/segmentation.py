"""Character-span segmentation F1 for TDD §18.4 M1."""

import math
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class CharacterSpan:
    start: int
    end: int


@dataclass(frozen=True)
class SpanMatch:
    gold_index: int
    predicted_index: int
    iou: float


@dataclass(frozen=True)
class SegmentationResult:
    gold_count: int
    predicted_count: int
    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float
    iou_threshold: float
    matches: tuple[SpanMatch, ...]


def _validated_spans(spans: Iterable[CharacterSpan], *, field: str) -> tuple[CharacterSpan, ...]:
    rows = tuple(spans)
    for span in rows:
        if not isinstance(span, CharacterSpan):
            raise ValueError(f"{field} spans must be CharacterSpan values")
        if (
            isinstance(span.start, bool)
            or not isinstance(span.start, int)
            or isinstance(span.end, bool)
            or not isinstance(span.end, int)
            or span.start < 0
            or span.end <= span.start
        ):
            raise ValueError("spans must be non-empty non-negative integer ranges")
    return rows


def character_iou(left: CharacterSpan, right: CharacterSpan) -> float:
    """Intersection-over-union for half-open Unicode code-point ranges."""
    intersection = max(0, min(left.end, right.end) - max(left.start, right.start))
    union = max(left.end, right.end) - min(left.start, right.start)
    return intersection / union if union > 0 else 0.0


def evaluate_segmentation(
    gold_spans: Iterable[CharacterSpan],
    predicted_spans: Iterable[CharacterSpan],
    *,
    iou_threshold: float = 0.80,
) -> SegmentationResult:
    """Greedily match spans by decreasing character IoU and compute F1.

    Ties are deterministic by gold index then prediction index. Empty gold is
    rejected so an empty/empty pair cannot be reported as a perfect score.
    """
    if (
        isinstance(iou_threshold, bool)
        or not isinstance(iou_threshold, (int, float))
        or not math.isfinite(iou_threshold)
        or not 0 < iou_threshold <= 1
    ):
        raise ValueError("iou_threshold must be greater than 0 and at most 1")
    gold = _validated_spans(gold_spans, field="gold")
    predicted = _validated_spans(predicted_spans, field="predicted")
    if not gold:
        raise ValueError("segmentation evaluation requires at least one gold span")

    candidates = [
        SpanMatch(gold_index, predicted_index, character_iou(gold_span, predicted_span))
        for gold_index, gold_span in enumerate(gold)
        for predicted_index, predicted_span in enumerate(predicted)
        if character_iou(gold_span, predicted_span) >= iou_threshold
    ]
    candidates.sort(key=lambda match: (-match.iou, match.gold_index, match.predicted_index))
    matched_gold: set[int] = set()
    matched_predicted: set[int] = set()
    matches = []
    for match in candidates:
        if match.gold_index not in matched_gold and match.predicted_index not in matched_predicted:
            matched_gold.add(match.gold_index)
            matched_predicted.add(match.predicted_index)
            matches.append(match)

    tp = len(matches)
    fp = len(predicted) - tp
    fn = len(gold) - tp
    precision = tp / len(predicted) if predicted else 0.0
    recall = tp / len(gold)
    f1 = 2 * tp / (2 * tp + fp + fn)
    return SegmentationResult(
        gold_count=len(gold),
        predicted_count=len(predicted),
        tp=tp,
        fp=fp,
        fn=fn,
        precision=precision,
        recall=recall,
        f1=f1,
        iou_threshold=float(iou_threshold),
        matches=tuple(matches),
    )
