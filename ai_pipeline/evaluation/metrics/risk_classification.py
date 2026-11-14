"""M2 (risk classification macro-F1), M2b (độ chính xác basis_type) và M9 (giải thích đúng) — BRD §8.3.

* M2: đơn vị chấm là bộ ba (điều khoản, vai trò, risk label) theo tài liệu. Báo per-class; macro-F1 CHỈ tính
  nhãn có support (gold) ≥ `min_support` (mặc định 5). Ngưỡng nghiệm thu ≥ 0.80 trên T1 (không tune trên T1).
* M2b: trên các bộ ba đã khớp ở M2, tỷ lệ basis_type dự đoán = gold. Báo kèm khoảng tin cậy; chưa có ngưỡng
  (OI-09). Severity không có chỉ số riêng (tra bảng từ nhãn, basis, vai trò).
* M9: mỗi output có nhãn chấm ĐÚNG / ĐÚNG_MỘT_PHẦN / SAI (người chấm; judge chỉ khi M6 đạt). Chỉ số chính
  = ĐÚNG / tổng (≥ 80% tạm); báo thêm tỷ lệ ĐÚNG_MỘT_PHẦN. Mẫu 40 output dùng chung với M3b.

Khoảng tin cậy: cluster bootstrap theo document, seed cố định. `clause_ref` phải đã được căn chỉnh gold ↔
pipeline trước (alignment.py, IoU ≥ 0.5); module này không tự căn chỉnh span.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from ai_pipeline.evaluation.metrics.bootstrap import bootstrap_cluster_interval

MIN_SUPPORT = 5
M9_LABELS = ("CORRECT", "PARTIAL", "WRONG")


@dataclass(frozen=True)
class RiskTriple:
    document_id: str
    clause_ref: str
    role: str
    risk_label: str
    basis_type: str = ""

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (self.document_id, self.clause_ref, self.role, self.risk_label)


def _per_class(gold: list[RiskTriple], pred: list[RiskTriple]) -> dict[str, dict]:
    gold_keys = {g.key for g in gold}
    pred_keys = {p.key for p in pred}
    labels = sorted({k[3] for k in gold_keys | pred_keys})
    out: dict[str, dict] = {}
    for label in labels:
        g = {k for k in gold_keys if k[3] == label}
        p = {k for k in pred_keys if k[3] == label}
        tp, fp, fn = len(g & p), len(p - g), len(g - p)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        out[label] = {"support": len(g), "tp": tp, "fp": fp, "fn": fn,
                      "precision": precision, "recall": recall, "f1": f1}
    return out


def _macro(per_class: dict[str, dict], min_support: int) -> float | None:
    scored = [v["f1"] for v in per_class.values() if v["support"] >= min_support]
    return sum(scored) / len(scored) if scored else None


def _check(rows: list[RiskTriple], name: str) -> None:
    keys = [r.key for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError(f"{name}: duplicate (document, clause, role, label) triple")
    if any(not r.document_id or not r.clause_ref or not r.role or not r.risk_label for r in rows):
        raise ValueError(f"{name}: empty field in triple")


def evaluate_risk_classification(gold: Iterable[RiskTriple], pred: Iterable[RiskTriple], *,
                                 min_support: int = MIN_SUPPORT, iterations: int = 1000,
                                 random_seed: int = 0) -> dict:
    gold, pred = list(gold), list(pred)
    _check(gold, "gold")
    _check(pred, "pred")
    per_class = _per_class(gold, pred)
    clusters: dict[str, list[tuple[str, RiskTriple]]] = {}
    for g in gold:
        clusters.setdefault(g.document_id, []).append(("g", g))
    for p in pred:
        clusters.setdefault(p.document_id, []).append(("p", p))

    def macro(rows):
        return _macro(_per_class([r for t, r in rows if t == "g"], [r for t, r in rows if t == "p"]), min_support)

    ci = bootstrap_cluster_interval(clusters, macro, iterations=iterations, random_seed=random_seed)
    return {
        "metric": "M2", "macro_f1": _macro(per_class, min_support), "macro_f1_ci95": [ci.low, ci.high],
        "min_support": min_support, "per_class": per_class,
        "macro_labels": sorted(k for k, v in per_class.items() if v["support"] >= min_support),
        "labels_below_min_support": sorted(k for k, v in per_class.items() if 0 < v["support"] < min_support),
        "gold_triples": len(gold), "predicted_triples": len(pred), "documents": len(clusters),
    }


def evaluate_basis_type(gold: Iterable[RiskTriple], pred: Iterable[RiskTriple], *,
                        iterations: int = 1000, random_seed: int = 0) -> dict:
    """M2b: chỉ trên bộ ba khớp ở M2."""
    gold_by = {g.key: g for g in gold}
    matched = [(gold_by[p.key], p) for p in pred if p.key in gold_by]
    if any(not g.basis_type or not p.basis_type for g, p in matched):
        raise ValueError("basis_type required on matched triples")
    correct = sum(g.basis_type == p.basis_type for g, p in matched)
    clusters: dict[str, list[bool]] = {}
    for g, p in matched:
        clusters.setdefault(g.document_id, []).append(g.basis_type == p.basis_type)
    ci = bootstrap_cluster_interval(clusters, lambda rows: sum(rows) / len(rows) if rows else None,
                                    iterations=iterations, random_seed=random_seed)
    confusion = Counter((g.basis_type, p.basis_type) for g, p in matched)
    return {"metric": "M2b", "matched": len(matched), "correct": correct,
            "accuracy": correct / len(matched) if matched else None, "accuracy_ci95": [ci.low, ci.high],
            "confusion": {f"{a}->{b}": n for (a, b), n in sorted(confusion.items())}}


@dataclass(frozen=True)
class ExplanationRating:
    output_id: str
    document_id: str
    rating: str  # CORRECT | PARTIAL | WRONG
    rater: str = ""


def evaluate_explanation_quality(ratings: Iterable[ExplanationRating], *, iterations: int = 1000,
                                 random_seed: int = 0) -> dict:
    """M9: tỷ lệ ĐÚNG (chính) và ĐÚNG_MỘT_PHẦN trên mẫu đã chấm."""
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
