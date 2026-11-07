"""Deterministic one-to-one alignment of half-open Unicode span offsets."""

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
    """Match highest IoU first; ties use Gold index then prediction index."""
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not 0 < threshold <= 1:
        raise ValueError("threshold must be in (0, 1]")
    candidates = []
    for gold_index, gold_span in enumerate(gold):
        for predicted_index, predicted_span in enumerate(predicted):
            score = span_iou(gold_span, predicted_span)
            if score >= threshold:
                candidates.append((-score, gold_index, predicted_index))
    candidates.sort()
    used_gold: set[int] = set()
    used_predicted: set[int] = set()
    matches = []
    for _, gold_index, predicted_index in candidates:
        if gold_index not in used_gold and predicted_index not in used_predicted:
            matches.append((gold_index, predicted_index))
            used_gold.add(gold_index)
            used_predicted.add(predicted_index)
    return matches
