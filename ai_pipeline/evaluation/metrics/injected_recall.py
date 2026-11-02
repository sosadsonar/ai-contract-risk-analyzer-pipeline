"""M5 exact matching recall for injected, deterministic risk examples."""

from collections import Counter
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class InjectedErrorCase:
    injection_id: str
    clause_ref: str
    role: str
    risk_label: str


@dataclass(frozen=True)
class RiskPrediction:
    clause_ref: str
    role: str
    risk_label: str


@dataclass(frozen=True)
class InjectedRecallResult:
    hits: int
    total: int
    recall: float | None
    missed_injection_ids: tuple[str, ...]


def evaluate_injected_recall(
    gold: Iterable[InjectedErrorCase], predictions: Iterable[RiskPrediction]
) -> InjectedRecallResult:
    cases = tuple(gold)
    ids = [case.injection_id for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("injection IDs must be unique")

    remaining = Counter((p.clause_ref, p.role, p.risk_label) for p in predictions)
    missed: list[str] = []
    for case in cases:
        key = (case.clause_ref, case.role, case.risk_label)
        if remaining[key]:
            remaining[key] -= 1
        else:
            missed.append(case.injection_id)
    total = len(cases)
    hits = total - len(missed)
    return InjectedRecallResult(hits, total, hits / total if total else None, tuple(missed))
