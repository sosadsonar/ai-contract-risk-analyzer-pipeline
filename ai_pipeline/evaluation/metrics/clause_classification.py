"""M7 sơ bộ — Clause classification macro-F1 (BRD §8.3, TDD §18.4). W4 (N1).

Quy đổi Gold → đầu ra pipeline (BRD 8.3): ghép một-một tham lam theo IoU span ≥ 0.5; Gold một nhãn
tính trúng khi nằm trong tập 1–3 nhãn dự đoán của clause khớp; Gold không khớp = sót; clause dự đoán
không khớp = báo thừa (mỗi nhãn của nó tính 1 FP). Macro chỉ tính nhãn có ≥ `min_support` mẫu Gold.

Hàm thuần, không I/O. Đây là đường đánh giá trên D1/dev — KHÔNG dùng để chỉnh theo T1/T2.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Sequence

IOU_ALIGN = 0.5
MIN_SUPPORT = 5


@dataclass(frozen=True)
class GoldSpan:
    start: int
    end: int
    label: str


@dataclass(frozen=True)
class PredClause:
    start: int
    end: int
    labels: tuple[str, ...]


def iou(a: tuple[int, int], b: tuple[int, int]) -> float:
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    union = max(a[1], b[1]) - min(a[0], b[0])
    return inter / union if union > 0 else 0.0


def align(gold: Sequence[GoldSpan], pred: Sequence[PredClause], threshold: float = IOU_ALIGN) -> list[tuple[int, int]]:
    """Ghép tham lam theo IoU giảm dần (ổn định theo chỉ số khi hòa). Trả [(gold_idx, pred_idx)]."""
    cands = []
    for gi, g in enumerate(gold):
        for pi, p in enumerate(pred):
            v = iou((g.start, g.end), (p.start, p.end))
            if v >= threshold:
                cands.append((-v, gi, pi))
    cands.sort()
    used_g: set[int] = set()
    used_p: set[int] = set()
    out = []
    for _, gi, pi in cands:
        if gi in used_g or pi in used_p:
            continue
        used_g.add(gi)
        used_p.add(pi)
        out.append((gi, pi))
    return out


def evaluate_clause_classification(
    gold: Sequence[GoldSpan], pred: Sequence[PredClause], *, min_support: int = MIN_SUPPORT
) -> dict:
    pairs = align(gold, pred)
    matched_g = {g for g, _ in pairs}
    matched_p = {p for _, p in pairs}
    tp: Counter = Counter()
    fp: Counter = Counter()
    fn: Counter = Counter()
    support: Counter = Counter(g.label for g in gold)
    for gi, pi in pairs:
        g, p = gold[gi], pred[pi]
        if g.label in p.labels:
            tp[g.label] += 1
        else:
            fn[g.label] += 1
        for lab in p.labels:
            if lab != g.label:
                fp[lab] += 1
    for gi, g in enumerate(gold):
        if gi not in matched_g:
            fn[g.label] += 1
    for pi, p in enumerate(pred):
        if pi not in matched_p:
            for lab in p.labels:
                fp[lab] += 1

    per_label = {}
    for lab in sorted(set(support) | set(fp)):
        t, f_p, f_n = tp[lab], fp[lab], fn[lab]
        prec = t / (t + f_p) if t + f_p else 0.0
        rec = t / (t + f_n) if t + f_n else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per_label[lab] = {"support": support[lab], "tp": t, "fp": f_p, "fn": f_n,
                          "precision": round(prec, 4), "recall": round(rec, 4), "f1": round(f1, 4)}
    scored = [v["f1"] for k, v in per_label.items() if support[k] >= min_support]
    return {
        "macro_f1": round(sum(scored) / len(scored), 4) if scored else None,
        "macro_labels": sorted(k for k in per_label if support[k] >= min_support),
        "labels_below_min_support": sorted(k for k in per_label if 0 < support[k] < min_support),
        "gold_total": len(gold),
        "pred_total": len(pred),
        "aligned": len(pairs),
        "gold_unmatched": len(gold) - len(matched_g),
        "pred_unmatched": len(pred) - len(matched_p),
        "per_label": per_label,
        "alignment_iou": IOU_ALIGN,
    }
