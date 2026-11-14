"""M9 — giải thích đúng (BRD §8.3, X-28): ĐÚNG / ĐÚNG_MỘT_PHẦN / SAI do người chấm (judge chỉ khi M6 đạt).

Chỉ số chính = ĐÚNG / tổng (≥ 80% tạm); báo thêm tỷ lệ ĐÚNG_MỘT_PHẦN. Mẫu 40 output dùng chung với M3b.
Khoảng tin cậy: cluster bootstrap theo document, seed cố định.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from ai_pipeline.evaluation.metrics.bootstrap import bootstrap_cluster_interval

M9_LABELS = ("CORRECT", "PARTIAL", "WRONG")


@dataclass(frozen=True)
class ExplanationRating:
    output_id: str
    document_id: str
    rating: str  # CORRECT | PARTIAL | WRONG
    rater: str = ""


def evaluate_explanation_quality(ratings: Iterable[ExplanationRating], *, iterations: int = 1000,
                                 random_seed: int = 0) -> dict:
    rows = list(ratings)
    ids = [r.output_id for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("one rating per output (adjudicate disagreements before scoring)")
    if any(r.rating not in M9_LABELS for r in rows):
        raise ValueError(f"rating must be one of {M9_LABELS}")
    counts = Counter(r.rating for r in rows)
    clusters: dict[str, list[ExplanationRating]] = {}
    for r in rows:
        clusters.setdefault(r.document_id, []).append(r)
    ci = bootstrap_cluster_interval(
        clusters, lambda rs: sum(x.rating == "CORRECT" for x in rs) / len(rs) if rs else None,
        iterations=iterations, random_seed=random_seed)
    total = len(rows)
    return {"metric": "M9", "total": total, "counts": {k: counts.get(k, 0) for k in M9_LABELS},
            "correct_rate": counts["CORRECT"] / total if total else None,
            "partial_rate": counts["PARTIAL"] / total if total else None,
            "correct_rate_ci95": [ci.low, ci.high]}
