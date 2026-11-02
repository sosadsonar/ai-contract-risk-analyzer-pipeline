"""Offline paired M8 adapter around a caller-provided retrieval function."""

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import TypeAlias

from ai_pipeline.evaluation.metrics.retrieval import (
    RetrievalCase,
    RetrievalMetricResult,
    evaluate_retrieval,
)


@dataclass(frozen=True)
class RetrievalRunInput:
    case_id: str
    masked_text: str
    predicted_labels: tuple[str, ...]
    analysis_date: date
    gold_citation_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.case_id, str) or not self.case_id.strip():
            raise ValueError("case_id must be non-empty")
        if not isinstance(self.masked_text, str) or not self.masked_text.strip():
            raise ValueError("masked_text must be non-empty")
        if not isinstance(self.predicted_labels, tuple) or not self.predicted_labels:
            raise ValueError("predicted_labels must be non-empty tuple")
        if any(not isinstance(label, str) or not label.strip() for label in self.predicted_labels):
            raise ValueError("predicted_labels must contain non-empty strings")
        if isinstance(self.analysis_date, datetime) or not isinstance(self.analysis_date, date):
            raise ValueError("analysis_date must be a date")
        if not isinstance(self.gold_citation_id, str) or not self.gold_citation_id.strip():
            raise ValueError("gold citation ID must be non-empty")


RetrieveCallback: TypeAlias = Callable[..., Sequence[str]]


def run_paired_m8(
    rows: Iterable[RetrievalRunInput],
    retrieve: RetrieveCallback,
    *,
    final_k: int,
    k: int = 5,
) -> RetrievalMetricResult:
    """Call retrieval twice per case with identical inputs and a shared budget."""
    inputs = tuple(rows)
    if not inputs:
        raise ValueError("retrieval evaluation requires at least one case")
    case_ids = [row.case_id for row in inputs]
    if len(set(case_ids)) != len(case_ids):
        raise ValueError("case_id values must be unique")
    if not callable(retrieve):
        raise ValueError("retrieve must be callable")

    paired: list[RetrievalCase] = []
    for row in inputs:
        if not isinstance(row, RetrievalRunInput):
            raise ValueError("each row must be a RetrievalRunInput")
        common = {
            "case": row,
            "masked_text": row.masked_text,
            "predicted_labels": row.predicted_labels,
            "analysis_date": row.analysis_date,
            "final_k": final_k,
        }
        graph_off = retrieve(**common, graph_enabled=False)
        graph_on = retrieve(**common, graph_enabled=True)
        paired.append(RetrievalCase(row.case_id, row.gold_citation_id, graph_off, graph_on))
    return evaluate_retrieval(paired, final_k=final_k, k=k)
