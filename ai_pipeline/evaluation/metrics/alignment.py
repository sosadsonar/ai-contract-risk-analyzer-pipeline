"""Deterministic one-to-one alignment of half-open Unicode span offsets."""

import re
from collections.abc import Sequence


def span_iou(left: tuple[int, int], right: tuple[int, int]) -> float:
    """Character IoU for valid ``[start, end)`` spans."""
    for start, end in (left, right):
        if isinstance(start, bool) or isinstance(end, bool) or not isinstance(start, int) or not isinstance(end, int):
            raise ValueError("span offsets must be integers")
        if start < 0 or end <= start:
            raise ValueError("span offsets must form a non-empty half-open interval")
    overlap = max(0, min(left[1], right[1]) - max(left[0], right[0]))
    union = max(left[1], right[1]) - min(left[0], right[0])
    return overlap / union


def greedy_align_spans(
    gold: Sequence[tuple[int, int]],
    predicted: Sequence[tuple[int, int]],
    *,
    threshold: float = 0.5,
) -> list[tuple[int, int]]:
    """Greedy one-to-one match, IoU >= threshold (BRD M7; SRS OI-10 §3.1 rule 6).

    Order: IoU descending; ties by gold start ascending, then predicted start ascending, then the
    original gold index and prediction index. Each span is matched at most once.
    """
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not 0 < threshold <= 1:
        raise ValueError("threshold must be in (0, 1]")
    candidates = []
    for gold_index, gold_span in enumerate(gold):
        for predicted_index, predicted_span in enumerate(predicted):
            score = span_iou(gold_span, predicted_span)
            if score >= threshold:
                candidates.append((-score, gold_span[0], predicted_span[0], gold_index, predicted_index))
    candidates.sort()
    used_gold: set[int] = set()
    used_predicted: set[int] = set()
    matches = []
    for *_, gold_index, predicted_index in candidates:
        if gold_index not in used_gold and predicted_index not in used_predicted:
            matches.append((gold_index, predicted_index))
            used_gold.add(gold_index)
            used_predicted.add(predicted_index)
    return matches


def diagnose_span_alignment(
    gold: Sequence[tuple[int, int]],
    predicted: Sequence[tuple[int, int]],
    *,
    text: str | None = None,
    clause_scope: tuple[int, int] | None = None,
    containment_threshold: float = 0.8,
) -> dict:
    """Report official greedy matches and separate many-to-one containment diagnostics.

    ``clause_scope`` must come from a source parser or explicitly reviewed bounds,
    not from Gold labels. This function never changes the official metric path.
    """
    if not 0 < containment_threshold <= 1:
        raise ValueError("containment_threshold must be in (0, 1]")
    if clause_scope is not None:
        span_iou(clause_scope, clause_scope)
    excluded: dict[int, str] = {}
    retained: list[tuple[int, tuple[int, int]]] = []
    heading_pattern = re.compile(r"(?:điều\s+\d+|mục\s+[ivxlcdm]+)\s*[.:]?", re.IGNORECASE)
    for index, span in enumerate(predicted):
        span_iou(span, span)
        if text is not None and span[1] > len(text):
            raise ValueError("prediction span exceeds source text")
        if clause_scope is not None and (span[1] <= clause_scope[0] or span[0] >= clause_scope[1]):
            excluded[index] = "outside_clause_scope"
        elif text is not None and not text[span[0]:span[1]].strip():
            excluded[index] = "blank_text"
        elif text is not None and heading_pattern.fullmatch(text[span[0]:span[1]].strip()):
            excluded[index] = "heading_only"
        else:
            retained.append((index, span))

    filtered = [span for _, span in retained]
    greedy = [(gold_index, retained[pred_index][0]) for gold_index, pred_index in greedy_align_spans(gold, filtered)]
    containment = []
    for gold_index, gold_span in enumerate(gold):
        span_iou(gold_span, gold_span)
        candidates = []
        for pred_index, pred_span in retained:
            intersection = max(0, min(gold_span[1], pred_span[1]) - max(gold_span[0], pred_span[0]))
            ratio = intersection / (gold_span[1] - gold_span[0])
            if ratio >= containment_threshold:
                candidates.append((-ratio, -span_iou(gold_span, pred_span), pred_index))
        if candidates:
            _, _, pred_index = min(candidates)
            containment.append((gold_index, pred_index))
    return {
        "greedy_iou_pairs": greedy,
        "containment_pairs": containment,
        "excluded_prediction_indices": excluded,
        "retained_prediction_indices": [index for index, _ in retained],
        "containment_threshold": containment_threshold,
        "greedy_iou_threshold": 0.5,
    }
