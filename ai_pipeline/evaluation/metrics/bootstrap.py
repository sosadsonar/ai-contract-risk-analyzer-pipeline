"""Deterministic cluster bootstrap confidence intervals."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from math import floor, isfinite
from random import Random
from typing import TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class ConfidenceInterval:
    """Percentile interval and the sampling metadata needed to interpret it."""

    low: float | None
    high: float | None
    confidence_level: float
    iterations: int
    cluster_count: int
    valid_replicate_count: int


def bootstrap_cluster_interval(
    clusters: Mapping[str, Sequence[T]],
    statistic: Callable[[Sequence[T]], float | None],
    *,
    iterations: int = 1000,
    random_seed: int = 0,
) -> ConfidenceInterval:
    """Bootstrap a statistic after resampling whole, independent clusters.

    Clusters are sampled with replacement in equal number to the number of
    non-empty input clusters. Their rows stay together. Replicates for which
    ``statistic`` is undefined or non-finite are excluded from the interval.
    """
    if isinstance(iterations, bool) or not isinstance(iterations, int) or iterations < 1:
        raise ValueError("iterations must be a positive integer")
    if isinstance(random_seed, bool) or not isinstance(random_seed, int):
        raise ValueError("random_seed must be an integer")
    if not callable(statistic):
        raise ValueError("statistic must be callable")

    grouped: dict[str, tuple[T, ...]] = {}
    for cluster_id, rows in clusters.items():
        if not isinstance(cluster_id, str) or not cluster_id.strip():
            raise ValueError("cluster IDs must be non-empty strings")
        grouped[cluster_id] = tuple(rows)

    cluster_ids = sorted(cluster_id for cluster_id, rows in grouped.items() if rows)
    cluster_count = len(cluster_ids)
    if cluster_count < 2:
        return ConfidenceInterval(
            low=None,
            high=None,
            confidence_level=0.95,
            iterations=iterations,
            cluster_count=cluster_count,
            valid_replicate_count=0,
        )

    rng = Random(random_seed)
    values: list[float] = []
    for _ in range(iterations):
        sampled_ids = [rng.choice(cluster_ids) for _ in cluster_ids]
        sampled_rows = tuple(row for cluster_id in sampled_ids for row in grouped[cluster_id])
        value = statistic(sampled_rows)
        if value is None:
            continue
        if not isinstance(value, (int, float)) or not isfinite(value):
            continue
        values.append(float(value))

    valid_replicate_count = len(values)
    if valid_replicate_count < 2:
        low = high = None
    else:
        values.sort()

        def percentile(probability: float) -> float:
            position = probability * (valid_replicate_count - 1)
            lower = floor(position)
            upper = min(lower + 1, valid_replicate_count - 1)
            weight = position - lower
            return values[lower] * (1 - weight) + values[upper] * weight

        tail_probability = (1 - 0.95) / 2
        low = percentile(tail_probability)
        high = percentile(1 - tail_probability)

    return ConfidenceInterval(
        low=low,
        high=high,
        confidence_level=0.95,
        iterations=iterations,
        cluster_count=cluster_count,
        valid_replicate_count=valid_replicate_count,
    )


def bootstrap_classification_intervals(
    cluster_counts: Mapping[str, Mapping[str, tuple[int, int, int]]],
    *,
    eligible_macro_labels: frozenset[str],
    reporting_labels: frozenset[str],
    iterations: int = 1000,
    random_seed: int = 0,
) -> tuple[ConfidenceInterval, dict[str, dict[str, ConfidenceInterval]]]:
    """Bootstrap macro and per-label scores from precomputed cluster counts.

    Each cluster maps labels to ``(true_positive, false_positive,
    false_negative)`` counts. Metrics with the same contributing cluster set
    share one resampling pass and one aggregation of those counts.
    """
    if isinstance(iterations, bool) or not isinstance(iterations, int) or iterations < 1:
        raise ValueError("iterations must be a positive integer")
    if isinstance(random_seed, bool) or not isinstance(random_seed, int):
        raise ValueError("random_seed must be an integer")

    normalized: dict[str, dict[str, tuple[int, int, int]]] = {}
    labels = set(eligible_macro_labels) | set(reporting_labels)
    for cluster_id, counts_by_label in cluster_counts.items():
        if not isinstance(cluster_id, str) or not cluster_id.strip():
            raise ValueError("cluster IDs must be non-empty strings")
        normalized_counts = {}
        for label, counts in counts_by_label.items():
            if not isinstance(label, str) or not label.strip():
                raise ValueError("labels must be non-empty strings")
            if (
                not isinstance(counts, tuple)
                or len(counts) != 3
                or any(isinstance(count, bool) or not isinstance(count, int) or count < 0 for count in counts)
            ):
                raise ValueError("classification counts must be three non-negative integers")
            normalized_counts[label] = counts
            labels.add(label)
        normalized[cluster_id] = normalized_counts

    eligible = frozenset(eligible_macro_labels)
    reporting = frozenset(labels)
    fields = ("precision", "recall", "f1")
    requests: dict[tuple[str | None, str], tuple[str, ...]] = {}
    macro_ids = tuple(sorted(
        cluster_id
        for cluster_id, counts in normalized.items()
        if any(sum(counts.get(label, (0, 0, 0))) > 0 for label in eligible)
    ))
    requests[(None, "f1")] = macro_ids
    for label in sorted(reporting):
        precision_ids = []
        recall_ids = []
        f1_ids = []
        for cluster_id, counts in normalized.items():
            tp, fp, fn = counts.get(label, (0, 0, 0))
            if tp + fp > 0:
                precision_ids.append(cluster_id)
            if tp + fn > 0:
                recall_ids.append(cluster_id)
            if tp + fp + fn > 0:
                f1_ids.append(cluster_id)
        requests[(label, "precision")] = tuple(sorted(precision_ids))
        requests[(label, "recall")] = tuple(sorted(recall_ids))
        requests[(label, "f1")] = tuple(sorted(f1_ids))

    grouped_requests: dict[tuple[str, ...], list[tuple[str | None, str]]] = {}
    for request, cluster_ids in requests.items():
        grouped_requests.setdefault(cluster_ids, []).append(request)
    values_by_request: dict[tuple[str | None, str], list[float]] = {
        request: [] for request in requests
    }

    for cluster_ids, group in grouped_requests.items():
        if len(cluster_ids) < 2:
            continue
        rng = Random(random_seed)
        needed_labels = {
            label for label, _ in group if label is not None
        } | (eligible if any(label is None for label, _ in group) else frozenset())
        for _ in range(iterations):
            totals = {label: [0, 0, 0] for label in needed_labels}
            for _draw in cluster_ids:
                sampled_id = rng.choice(cluster_ids)
                for label, (tp, fp, fn) in normalized[sampled_id].items():
                    if label in totals:
                        current = totals[label]
                        current[0] += tp
                        current[1] += fp
                        current[2] += fn

            for label, field in group:
                if label is None:
                    if not any(sum(totals.get(candidate, (0, 0, 0))) > 0 for candidate in eligible):
                        continue
                    f1_values = []
                    for candidate in eligible:
                        tp, fp, fn = totals.get(candidate, (0, 0, 0))
                        denominator = 2 * tp + fp + fn
                        f1_values.append(2 * tp / denominator if denominator else 0.0)
                    if f1_values:
                        values_by_request[(label, field)].append(sum(f1_values) / len(f1_values))
                    continue

                tp, fp, fn = totals[label]
                if field == "precision":
                    denominator = tp + fp
                    value = tp / denominator if denominator else None
                elif field == "recall":
                    denominator = tp + fn
                    value = tp / denominator if denominator else None
                else:
                    denominator = 2 * tp + fp + fn
                    value = 2 * tp / denominator if denominator else None
                if value is not None:
                    values_by_request[(label, field)].append(value)

    intervals = {
        request: _interval_from_values(values, iterations, len(requests[request]))
        for request, values in values_by_request.items()
    }
    macro = intervals[(None, "f1")]
    per_class = {
        label: {field: intervals[(label, field)] for field in fields}
        for label in sorted(reporting)
    }
    return macro, per_class


def _interval_from_values(values: list[float], iterations: int, cluster_count: int) -> ConfidenceInterval:
    valid_replicate_count = len(values)
    if valid_replicate_count < 2:
        low = high = None
    else:
        ordered = sorted(values)

        def percentile(probability: float) -> float:
            position = probability * (valid_replicate_count - 1)
            lower = floor(position)
            upper = min(lower + 1, valid_replicate_count - 1)
            weight = position - lower
            return ordered[lower] * (1 - weight) + ordered[upper] * weight

        tail_probability = (1 - 0.95) / 2
        low = percentile(tail_probability)
        high = percentile(1 - tail_probability)
    return ConfidenceInterval(
        low=low,
        high=high,
        confidence_level=0.95,
        iterations=iterations,
        cluster_count=cluster_count,
        valid_replicate_count=valid_replicate_count,
    )
