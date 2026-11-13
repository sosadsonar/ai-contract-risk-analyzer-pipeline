"""M2/M2b evaluation of (clause, role, risk label), with optional span alignment."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from statistics import NormalDist
from typing import Sequence

from app.core.enums import BasisType, Role
from app.risk.taxonomy import RISK_LABELS

from ai_pipeline.evaluation.metrics.alignment import greedy_align_spans, span_iou


@dataclass(frozen=True)
class RiskRecord:
    clause_id: str
    role: str
    risk_label: str
    basis_type: str
    start_char: int | None = None
    end_char: int | None = None
    document_id: str = ""
    offset_quality: str = "EXACT"


def map_dev_candidate_to_risk_labels(
    candidates: tuple[tuple[str, str], ...],
) -> tuple[tuple[str, str], ...]:
    """Legacy M5 label bridge only; never synthesize M2 Gold from clause labels."""
    mapping = {"EMPLOYEE_OBLIGATIONS_DISCIPLINE": "DISCIPLINE_OBLIGATION",
               "DEPOSIT_DOCUMENT_HELD": "DEPOSIT_DOCUMENT_HELD"}
    return tuple((role, mapping[label]) for role, label in candidates)


def _validate(records: Sequence[RiskRecord]) -> dict[tuple[str, str], tuple[int, int] | None]:
    spans: dict[tuple[str, str], tuple[int, int] | None] = {}
    seen: set[tuple[str, str, str, str]] = set()
    for item in records:
        if not item.clause_id or item.role not in {r.value for r in Role}:
            raise ValueError("invalid clause ID or role")
        if item.risk_label not in RISK_LABELS or item.basis_type not in {b.value for b in BasisType}:
            raise ValueError("invalid risk label or basis type")
        triple = (item.document_id, item.clause_id, item.role, item.risk_label)
        if triple in seen:
            raise ValueError("duplicate risk triple")
        seen.add(triple)
        if (item.start_char is None) != (item.end_char is None):
            raise ValueError("incomplete span")
        span = None if item.start_char is None else (item.start_char, item.end_char)
        if span is not None:
            span_iou(span, span)
        key = (item.document_id, item.clause_id)
        if key in spans and spans[key] != span:
            raise ValueError("inconsistent clause span")
        spans[key] = span
    return spans


def _align_clauses(gold_spans, pred_spans) -> dict[tuple[str, str], tuple[str, str]]:
    mapped = {key: key for key in pred_spans if key in gold_spans}
    docs = {key[0] for key in gold_spans} | {key[0] for key in pred_spans}
    for doc in docs:
        gold_keys = [key for key, span in gold_spans.items()
                     if key[0] == doc and key not in mapped.values() and span is not None]
        pred_keys = [key for key, span in pred_spans.items()
                     if key[0] == doc and key not in mapped and span is not None]
        if gold_keys and pred_keys:
            pairs = greedy_align_spans([gold_spans[key] for key in gold_keys],
                                       [pred_spans[key] for key in pred_keys], threshold=0.5)
            mapped.update({pred_keys[pi]: gold_keys[gi] for gi, pi in pairs})
            used_gold = {gi for gi, _ in pairs}
            used_pred = {pi for _, pi in pairs}
            containment_candidates = []
            for gi, gold_key in enumerate(gold_keys):
                if gi in used_gold:
                    continue
                gs, ge = gold_spans[gold_key]
                for pi, pred_key in enumerate(pred_keys):
                    if pi in used_pred:
                        continue
                    ps, pe = pred_spans[pred_key]
                    overlap = max(0, min(ge, pe) - max(gs, ps))
                    coverage = overlap / (ge - gs)
                    if coverage >= 0.8:
                        containment_candidates.append(
                            (-coverage, -span_iou((gs, ge), (ps, pe)), gi, pi))
            for _, _, gi, pi in sorted(containment_candidates):
                if gi not in used_gold and pi not in used_pred:
                    mapped[pred_keys[pi]] = gold_keys[gi]
                    used_gold.add(gi)
                    used_pred.add(pi)
    return mapped


def _wilson(successes: int, total: int) -> tuple[float, float] | None:
    if not total:
        return None
    z = NormalDist().inv_cdf(0.975)
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def _merged_excluded_regions(regions: Sequence[dict]) -> dict[tuple[str, str], list[tuple[int, int]]]:
    grouped: dict[tuple[str, str], list[tuple[int, int]]] = {}
    for region in regions:
        start, end = region["start_char"], region["end_char"]
        if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start:
            raise ValueError("invalid excluded scope region")
        key = (region["document_id"].removeprefix("T1:"), region["role"])
        grouped.setdefault(key, []).append((start, end))
    for key, intervals in grouped.items():
        merged = []
        for start, end in sorted(intervals):
            if merged and start - merged[-1][1] <= 15:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        grouped[key] = merged
    return grouped


def evaluate_risk_classification(
    gold: Sequence[RiskRecord], predicted: Sequence[RiskRecord],
    *, require_gold_spans: bool = False,
    excluded_scope_regions: Sequence[dict] = (),
) -> dict:
    """Score all 21 labels; zero-support labels receive F1=0 in all-label macro."""
    merged_regions = _merged_excluded_regions(excluded_scope_regions)

    excluded_gold = sum(
        item.offset_quality == "CONTEXT" or
        (require_gold_spans and (item.start_char is None or item.end_char is None))
        for item in gold
    )
    gold = [item for item in gold if item.offset_quality != "CONTEXT" and
            (not require_gold_spans or
             (item.start_char is not None and item.end_char is not None))]

    def within_scope(records: Sequence[RiskRecord]) -> tuple[list[RiskRecord], list[dict], list[dict]]:
        included = []
        excluded = []
        warnings = []
        for item in records:
            regions = merged_regions.get((item.document_id.removeprefix("T1:"), item.role), [])
            if not regions:
                included.append(item)
                continue
            if item.start_char is None or item.end_char is None:
                raise ValueError("cannot check scope exclusion without a span")
            overlaps = [(max(0, min(item.end_char, end) - max(item.start_char, start)),
                         end - start, start, end) for start, end in regions]
            overlaps = [part for part in overlaps if part[0] > 0]
            if not overlaps:
                included.append(item)
            else:
                length = item.end_char - item.start_char
                total_intersection = sum(part[0] for part in overlaps)
                above = total_intersection / length >= 0.5 or any(
                    intersection / region_length >= 0.5 or
                    intersection / (length + region_length - intersection) >= 0.5
                    for intersection, region_length, _, _ in overlaps)
                entry = {"document_id": item.document_id, "clause_id": item.clause_id,
                         "role": item.role, "risk_label": item.risk_label,
                         "start_char": item.start_char, "end_char": item.end_char,
                         "intersection_chars": total_intersection}
                if above:
                    excluded.append(entry)
                else:
                    included.append(item)
                    warnings.append(entry)
        return included, excluded, warnings

    gold, scope_excluded_gold, gold_overlap_warnings = within_scope(gold)
    predicted, scope_excluded_predicted, pred_overlap_warnings = within_scope(predicted)
    gold_spans, pred_spans = _validate(gold), _validate(predicted)
    mapping = _align_clauses(gold_spans, pred_spans)
    gold_keys = {(r.document_id, r.clause_id, r.role, r.risk_label) for r in gold}
    pred_keys = {(mapping.get((r.document_id, r.clause_id),
                              (r.document_id, "__unmatched__" + r.clause_id))[0],
                  mapping.get((r.document_id, r.clause_id),
                              (r.document_id, "__unmatched__" + r.clause_id))[1],
                  r.role, r.risk_label) for r in predicted}
    tp_keys = gold_keys & pred_keys
    fp_keys = pred_keys - gold_keys
    fn_keys = gold_keys - pred_keys
    support = Counter(r.risk_label for r in gold)
    pred_support = Counter(r.risk_label for r in predicted)
    tp, fp, fn = (Counter(key[3] for key in keys) for keys in (tp_keys, fp_keys, fn_keys))
    per_label = {}
    for label in RISK_LABELS:
        t, f_p, f_n = tp[label], fp[label], fn[label]
        precision = t / (t + f_p) if t + f_p else 0.0
        recall = t / (t + f_n) if t + f_n else 0.0
        f1 = 2 * t / (2 * t + f_p + f_n) if 2 * t + f_p + f_n else 0.0
        per_label[label] = {"tp": t, "fp": f_p, "fn": f_n,
                            "precision": precision, "recall": recall, "f1": f1,
                            "gold_support": support[label], "pred_support": pred_support[label]}
    totals = {"tp": len(tp_keys), "fp": len(fp_keys), "fn": len(fn_keys)}
    denom = 2 * totals["tp"] + totals["fp"] + totals["fn"]
    present = [label for label in RISK_LABELS if support[label] > 0]
    gold_basis = {(r.document_id, r.clause_id, r.role, r.risk_label): r.basis_type for r in gold}
    pred_basis = {}
    for r in predicted:
        mapped = mapping.get((r.document_id, r.clause_id))
        if mapped is not None:
            pred_basis[(*mapped, r.role, r.risk_label)] = r.basis_type
    basis_correct = sum(gold_basis[key] == pred_basis[key] for key in tp_keys)
    return {
        "per_label": per_label,
        "macro_f1_present_labels": (sum(per_label[label]["f1"] for label in present) / len(present)
                                    if present else None),
        "macro_f1_all_21_labels": sum(row["f1"] for row in per_label.values()) / len(RISK_LABELS),
        "micro_counts": totals,
        "micro_precision": totals["tp"] / (totals["tp"] + totals["fp"])
        if totals["tp"] + totals["fp"] else 0.0,
        "micro_recall": totals["tp"] / (totals["tp"] + totals["fn"])
        if totals["tp"] + totals["fn"] else 0.0,
        "micro_f1": 2 * totals["tp"] / denom if denom else 0.0,
        "gold_label_coverage": {"present": len(present), "total": len(RISK_LABELS)},
        "full_taxonomy_coverage": len(present) == len(RISK_LABELS),
        "alignment_pairs": len(mapping),
        "excluded_gold_unalignable": excluded_gold,
        "excluded_scope_gold_records": len(scope_excluded_gold),
        "excluded_scope_predicted_records": len(scope_excluded_predicted),
        "merged_excluded_regions": [
            {"document_id": doc, "role": role, "start_char": start, "end_char": end}
            for (doc, role), intervals in sorted(merged_regions.items())
            for start, end in intervals],
        "excluded_overlap_predictions": scope_excluded_predicted,
        "partial_excluded_overlap_warnings": pred_overlap_warnings,
        "partial_excluded_gold_overlap_warnings": gold_overlap_warnings,
        "basis_type_accuracy": basis_correct / len(tp_keys) if tp_keys else None,
        "basis_type_ci95": _wilson(basis_correct, len(tp_keys)),
        "basis_type_support": len(tp_keys),
    }
