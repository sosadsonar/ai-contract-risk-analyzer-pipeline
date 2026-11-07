"""M5 exact matching recall for injected, deterministic risk examples."""

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from ai_pipeline.evaluation.metrics.bootstrap import bootstrap_cluster_interval


@dataclass(frozen=True)
class InjectedErrorCase:
    injection_id: str
    clause_ref: str
    role: str
    risk_label: str
    source_document_id: str | None = None


@dataclass(frozen=True)
class RiskPrediction:
    clause_ref: str
    role: str
    risk_label: str
    source_document_id: str | None = None


@dataclass(frozen=True)
class InjectedRecallResult:
    hits: int
    total: int
    recall: float | None
    missed_injection_ids: tuple[str, ...]
    recall_ci95_low: float | None = None
    recall_ci95_high: float | None = None
    bootstrap_cluster_count: int = 0
    bootstrap_iterations: int = 1000
    bootstrap_valid_replicate_count: int = 0


def evaluate_injected_recall(
    gold: Iterable[InjectedErrorCase], predictions: Iterable[RiskPrediction]
) -> InjectedRecallResult:
    cases = tuple(gold)
    prediction_rows = tuple(predictions)
    gold_has_documents = any(case.source_document_id is not None for case in cases)
    predictions_have_documents = any(
        prediction.source_document_id is not None for prediction in prediction_rows
    )
    if (gold_has_documents and prediction_rows and not predictions_have_documents) or (
        predictions_have_documents and not gold_has_documents
    ):
        raise ValueError("source_document_id is required on both gold and predictions")
    if gold_has_documents and (
        any(not case.source_document_id for case in cases)
        or any(not prediction.source_document_id for prediction in prediction_rows)
    ):
        raise ValueError("source_document_id is required for every gold case and prediction")
    gold_documents_by_key: dict[tuple[str, str, str], set[str]] = {}
    if gold_has_documents:
        for case in cases:
            if not isinstance(case.source_document_id, str) or not case.source_document_id.strip():
                raise ValueError("source_document_id must be non-empty")
            gold_documents_by_key.setdefault(
                (case.clause_ref, case.role, case.risk_label), set()
            ).add(case.source_document_id)
        for prediction in prediction_rows:
            if not isinstance(prediction.source_document_id, str) or not prediction.source_document_id.strip():
                raise ValueError("source_document_id must be non-empty")
            key = (prediction.clause_ref, prediction.role, prediction.risk_label)
            if key in gold_documents_by_key and prediction.source_document_id not in gold_documents_by_key[key]:
                raise ValueError("prediction source_document_id conflicts with matching gold case")
    ids = [case.injection_id for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("injection IDs must be unique")

    remaining = Counter((p.clause_ref, p.role, p.risk_label) for p in prediction_rows)
    missed: list[str] = []
    for case in cases:
        key = (case.clause_ref, case.role, case.risk_label)
        if remaining[key]:
            remaining[key] -= 1
        else:
            missed.append(case.injection_id)
    total = len(cases)
    hits = total - len(missed)
    by_document_gold: dict[str, list[InjectedErrorCase]] = {}
    by_document_predictions: dict[str, list[RiskPrediction]] = {}
    for case in cases:
        by_document_gold.setdefault(case.source_document_id or "__unspecified__", []).append(case)
    for prediction in prediction_rows:
        by_document_predictions.setdefault(
            prediction.source_document_id or "__unspecified__", []
        ).append(prediction)
    clusters = {
        document_id: ((tuple(document_gold), tuple(by_document_predictions.get(document_id, ()))),)
        for document_id, document_gold in by_document_gold.items()
    }

    def sampled_recall(rows):
        sampled_gold = [case for gold_rows, _ in rows for case in gold_rows]
        sampled_predictions = [prediction for _, predictions_for_doc in rows for prediction in predictions_for_doc]
        if not sampled_gold:
            return None
        available = Counter(
            (prediction.clause_ref, prediction.role, prediction.risk_label)
            for prediction in sampled_predictions
        )
        sampled_hits = 0
        for case in sampled_gold:
            key = (case.clause_ref, case.role, case.risk_label)
            if available[key]:
                available[key] -= 1
                sampled_hits += 1
        return sampled_hits / len(sampled_gold)

    interval = bootstrap_cluster_interval(clusters, sampled_recall)
    return InjectedRecallResult(
        hits, total, hits / total if total else None, tuple(missed),
        interval.low, interval.high, interval.cluster_count, interval.iterations,
        interval.valid_replicate_count,
    )
