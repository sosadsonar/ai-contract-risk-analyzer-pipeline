"""Paired graph-on/off Recall@k calculation for injected-error evaluation."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalCase:
    """One injected error and its gold citation under both retrieval runs."""

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
    cases: Iterable[RetrievalCase], *, final_k: int, k: int = 5
) -> RetrievalMetricResult:
    """Compare paired Recall@k while enforcing one shared final candidate budget."""
    if isinstance(final_k, bool) or not isinstance(final_k, int) or final_k < 1:
        raise ValueError("final_k must be a positive integer")
    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= final_k:
        raise ValueError("k must be between 1 and final_k")
    rows = tuple(cases)
    if not rows:
        raise ValueError("retrieval evaluation requires at least one case")

    seen: set[str] = set()
    off_hits = on_hits = added = 0
    for case in rows:
        if not isinstance(case, RetrievalCase):
            raise ValueError("each retrieval row must be a RetrievalCase")
        if not isinstance(case.case_id, str) or not case.case_id.strip():
            raise ValueError("case_id must be non-empty")
        if case.case_id in seen:
            raise ValueError("case_id values must be unique")
        seen.add(case.case_id)
        if not isinstance(case.gold_citation_id, str) or not case.gold_citation_id.strip():
            raise ValueError("gold citation ID must be non-empty")
        off = _validate_candidate_ids(case.baseline_candidate_ids, final_k=final_k)
        on = _validate_candidate_ids(case.graph_candidate_ids, final_k=final_k)
        off_hits += case.gold_citation_id in off[:k]
        on_hits += case.gold_citation_id in on[:k]
        added += len(set(on) - set(off))

    total = len(rows)
    return RetrievalMetricResult(
        k, final_k, RecallSummary(off_hits, total, off_hits / total),
        RecallSummary(on_hits, total, on_hits / total), added,
    )
