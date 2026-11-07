"""Per-label clause classification metrics for TDD §18.4 M7."""

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

MIN_GOLD_SUPPORT = 5


@dataclass(frozen=True)
class ClauseClassificationCase:
    clause_id: str
    gold_labels: Sequence[str]
    predicted_labels: Sequence[str]


@dataclass(frozen=True)
class ClauseClassMetric:
    label: str
    support: int
    predicted_support: int
    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float
    included_in_macro: bool
    precision_ci95_low: float | None = None
    precision_ci95_high: float | None = None
    recall_ci95_low: float | None = None
    recall_ci95_high: float | None = None
    f1_ci95_low: float | None = None
    f1_ci95_high: float | None = None
    precision_bootstrap_cluster_count: int = 0
    precision_valid_replicate_count: int = 0
    precision_ci95_reason: str | None = None
    recall_bootstrap_cluster_count: int = 0
    recall_valid_replicate_count: int = 0
    recall_ci95_reason: str | None = None
    f1_bootstrap_cluster_count: int = 0
    f1_valid_replicate_count: int = 0
    f1_ci95_reason: str | None = None


@dataclass(frozen=True)
class ClauseClassificationResult:
    total_clauses: int
    macro_f1: float | None
    macro_class_count: int
    per_class: tuple[ClauseClassMetric, ...]
    split_name: str | None = None
    split_status: str | None = None
    source_dataset_sha256: str | None = None
    split_manifest_sha256: str | None = None
    excluded_clause_count: int = 0
    macro_f1_ci95_low: float | None = None
    macro_f1_ci95_high: float | None = None
    bootstrap_cluster_count: int = 0
    bootstrap_iterations: int = 1000
    bootstrap_valid_replicate_count: int = 0
    macro_f1_ci95_reason: str | None = None


def _labels(
    values: Sequence[str], *, clause_id: str, field: str, allow_empty: bool = False
) -> frozenset[str]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ValueError(f"{clause_id}: {field} must be a sequence of labels")
    if any(not isinstance(label, str) or not label.strip() for label in values):
        raise ValueError("labels must be non-empty strings")
    if not values and not allow_empty:
        raise ValueError("gold labels must not be empty")
    if len(set(values)) != len(values):
        raise ValueError("labels must be unique per clause")
    return frozenset(values)


def evaluate_clause_classification(
    cases: Iterable[ClauseClassificationCase],
    *,
    eligible_macro_labels: frozenset[str] | None = None,
    reporting_labels: frozenset[str] | None = None,
) -> ClauseClassificationResult:
    """Compute binary per-label F1 over (clause, label) pairs.

    Macro F1 includes only labels with at least five gold-positive clauses,
    matching BRD §8.3. If no class reaches that support, macro F1 is undefined.
    """
    rows = tuple(cases)
    if not rows:
        raise ValueError("classification evaluation requires at least one clause")

    seen: set[str] = set()
    gold_by_clause: list[frozenset[str]] = []
    predicted_by_clause: list[frozenset[str]] = []
    for case in rows:
        if not isinstance(case, ClauseClassificationCase):
            raise ValueError("each row must be a ClauseClassificationCase")
        if not isinstance(case.clause_id, str) or not case.clause_id.strip():
            raise ValueError("clause_id must be non-empty")
        if case.clause_id in seen:
            raise ValueError("clause IDs must be unique")
        seen.add(case.clause_id)
        gold_by_clause.append(
            _labels(case.gold_labels, clause_id=case.clause_id, field="gold_labels")
        )
        predicted_by_clause.append(
            _labels(
                case.predicted_labels,
                clause_id=case.clause_id,
                field="predicted_labels",
                allow_empty=True,
            )
        )

    gold_support: Counter[str] = Counter()
    predicted_support: Counter[str] = Counter()
    true_positive: Counter[str] = Counter()
    for gold, predicted in zip(gold_by_clause, predicted_by_clause, strict=True):
        gold_support.update(gold)
        predicted_support.update(predicted)
        true_positive.update(gold & predicted)

    metrics = []
    labels = set(gold_support) | set(predicted_support)
    if eligible_macro_labels is not None:
        labels |= eligible_macro_labels
    if reporting_labels is not None:
        labels |= reporting_labels
    for label in sorted(labels):
        tp = true_positive[label]
        fp = predicted_support[label] - tp
        fn = gold_support[label] - tp
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0
        support = gold_support[label]
        metrics.append(
            ClauseClassMetric(
                label=label,
                support=support,
                predicted_support=predicted_support[label],
                tp=tp,
                fp=fp,
                fn=fn,
                precision=precision,
                recall=recall,
                f1=f1,
                included_in_macro=(
                    label in eligible_macro_labels
                    if eligible_macro_labels is not None
                    else support >= MIN_GOLD_SUPPORT
                ),
            )
        )

    eligible_f1 = [metric.f1 for metric in metrics if metric.included_in_macro]
    macro_f1 = sum(eligible_f1) / len(eligible_f1) if eligible_f1 else None
    return ClauseClassificationResult(
        total_clauses=len(rows),
        macro_f1=macro_f1,
        macro_class_count=len(eligible_f1),
        per_class=tuple(metrics),
    )
