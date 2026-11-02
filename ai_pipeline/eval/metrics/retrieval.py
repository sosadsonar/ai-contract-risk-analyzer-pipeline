"""Paired graph-on/off Recall@k calculation for injected-error evaluation."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalCase:
    """One injected error and its gold law citation under both retrieval runs."""

    case_id: str
    gold_citation_id: str
    baseline_candidate_ids: Sequence[str]
    graph_candidate_ids: Sequence[str]


@dataclass(frozen=True)
class RecallSummary:
    hits: int
    total: int
    recall: float


@dataclass(frozen=True)
class RetrievalMetricResult:
    k: int
    final_k: int
    graph_off: RecallSummary
    graph_on: RecallSummary
    graph_added_candidate_count: int


def _validate_candidate_ids(values: Sequence[str], *, final_k: int) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ValueError("candidate citation IDs must be a sequence")
    candidate_ids = tuple(values)
    if any(not isinstance(value, str) or not value.strip() for value in candidate_ids):
        raise ValueError("candidate citation IDs must be non-empty and unique")
    if len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("candidate citation IDs must be non-empty and unique")
    if len(candidate_ids) > final_k:
        raise ValueError("candidate list exceeds final_k")
    return candidate_ids


def evaluate_retrieval(
    cases: Iterable[RetrievalCase],
    *,
    final_k: int,
    k: int = 5,
) -> RetrievalMetricResult:
    """Compare paired Recall@k while enforcing one shared final candidate budget."""
    if isinstance(final_k, bool) or not isinstance(final_k, int) or final_k < 1:
        raise ValueError("final_k must be a positive integer")
    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= final_k:
        raise ValueError("k must be between 1 and final_k")

    rows = tuple(cases)
    if not rows:
        raise ValueError("retrieval evaluation requires at least one case")

    seen_case_ids: set[str] = set()
    baseline_hits = graph_hits = graph_added = 0
    for case in rows:
        if not isinstance(case, RetrievalCase):
            raise ValueError("each retrieval row must be a RetrievalCase")
        if not isinstance(case.case_id, str) or not case.case_id.strip():
            raise ValueError("case_id must be non-empty")
        if case.case_id in seen_case_ids:
            raise ValueError("case_id values must be unique")
        seen_case_ids.add(case.case_id)
        if not isinstance(case.gold_citation_id, str) or not case.gold_citation_id.strip():
            raise ValueError("gold citation ID must be non-empty")

        baseline_ids = _validate_candidate_ids(case.baseline_candidate_ids, final_k=final_k)
        graph_ids = _validate_candidate_ids(case.graph_candidate_ids, final_k=final_k)
        baseline_hits += case.gold_citation_id in baseline_ids[:k]
        graph_hits += case.gold_citation_id in graph_ids[:k]
        graph_added += len(set(graph_ids) - set(baseline_ids))

    total = len(rows)
    return RetrievalMetricResult(
        k=k,
        final_k=final_k,
        graph_off=RecallSummary(baseline_hits, total, baseline_hits / total),
        graph_on=RecallSummary(graph_hits, total, graph_hits / total),
        graph_added_candidate_count=graph_added,
    )
