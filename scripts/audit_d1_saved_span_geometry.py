"""Audit saved D1 span geometry without publishing contract text or inferring labels."""

import argparse
import csv
import difflib
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from app.document.canonicalizer import canonicalize

from ai_pipeline.evaluation.metrics.alignment import greedy_align_spans

DOCUMENTS = ("HDLD001", "HDLD002", "HDLD003", "HDLD004")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def audit(data_root: Path, predictions_path: Path, unmatched_path: Path, report_path: Path) -> dict:
    """Compare predictions with pinned canonical D1 Gold and a claimed unmatched list."""
    restricted = data_root / "data/intake/restricted"
    with (data_root / "data/processed/clauses_v06.csv").open(encoding="utf-8-sig", newline="") as stream:
        exact = {row["clause_id"] for row in csv.DictReader(stream) if row["offset_quality"] == "EXACT"}
    predictions = _load(predictions_path)
    claimed_unmatched = _load(unmatched_path)
    original_report = _load(report_path)
    if not isinstance(predictions, list) or not isinstance(claimed_unmatched, list):
        raise ValueError("prediction and unmatched artifacts must be arrays")

    per_document = []
    computed_unmatched = set()
    support: Counter[str] = Counter()
    matched_support: Counter[str] = Counter()
    total_exact_quotes = total_whitespace_only = 0
    total_gold = total_predicted = total_matches = 0
    source_parity_count = 0
    for document in DOCUMENTS:
        canonical_path = restricted / "D1_m1_runtime_predictions_v01" / f"{document}.canonical_nfc.txt"
        canonical = canonical_path.read_text(encoding="utf-8")
        raw_path = data_root / "data/processed/raw_text" / f"{document}.txt"
        recomputed_canonical = canonicalize([raw_path.read_text(encoding="utf-8")])
        source_parity = canonical == recomputed_canonical
        source_parity_count += source_parity
        source_differences = [
            (start, end)
            for tag, start, end, _, _ in difflib.SequenceMatcher(
                None, canonical, recomputed_canonical, autojunk=False
            ).get_opcodes()
            if tag != "equal"
        ]
        source_difference_operations = len(source_differences)
        gold_file = restricted / "D1_m1_gold_v01" / f"{document}.gold_segmentation.json"
        gold_json = _load(gold_file)
        if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != gold_json["source_sha256"]:
            raise ValueError(f"canonical source hash mismatch: {document}")
        labels_json = _load(restricted / "D1_clause_label_gold_v01" / f"{document}.gold_clause_labels.json")
        labels = {row["clause_id"]: row["labels"] for row in labels_json["items"]}
        gold = [
            row for row in gold_json["segments"]
            if row.get("gold_clause_ref") in exact and row.get("gold_clause_ref") in labels
        ]
        gold_intersecting_source_differences = sum(
            any(
                row["start_char"] < max(start + 1, end)
                and start < row["end_char"]
                for start, end in source_differences
            )
            for row in gold
        )
        all_segments = sorted(gold_json["segments"], key=lambda row: row["start_char"])
        if all_segments[0]["start_char"] != 0 or all_segments[-1]["end_char"] != len(canonical):
            raise ValueError(f"Gold does not reach canonical source boundaries: {document}")
        if any(left["end_char"] > right["start_char"] for left, right in zip(all_segments, all_segments[1:])):
            raise ValueError(f"overlapping Gold segments: {document}")
        gap_ranges = [
            (left["end_char"], right["start_char"])
            for left, right in zip(all_segments, all_segments[1:])
            if left["end_char"] < right["start_char"]
        ]
        if any(not canonical[start:end].isspace() for start, end in gap_ranges):
            raise ValueError(f"non-whitespace Gold coverage gap: {document}")
        predicted = [row for row in predictions if row.get("contract_id") == document]
        if len({row["clause_id"] for row in predicted}) != len(predicted):
            raise ValueError(f"duplicate predicted clause ID: {document}")
        exact_quotes = whitespace_only = 0
        for row in predicted:
            start, end = row["start_char"], row["end_char"]
            if not 0 <= start < end <= len(canonical):
                raise ValueError(f"prediction offset out of bounds: {document}/{row['clause_id']}")
            sliced = canonical[start:end]
            if sliced == row["text"]:
                exact_quotes += 1
            elif re.sub(r"\s+", " ", sliced).strip() == re.sub(r"\s+", " ", row["text"]).strip():
                whitespace_only += 1
            else:
                raise ValueError(f"non-whitespace quote mismatch: {document}/{row['clause_id']}")
        pairs = greedy_align_spans(
            [(row["start_char"], row["end_char"]) for row in gold],
            [(row["start_char"], row["end_char"]) for row in predicted],
        )
        matched_gold = {index for index, _ in pairs}
        for index, row in enumerate(gold):
            label_values = labels[row["gold_clause_ref"]]
            if len(label_values) != 1:
                raise ValueError("optimistic ceiling requires one Gold label per D1 clause")
            label = label_values[0]
            support[label] += 1
            if index in matched_gold:
                matched_support[label] += 1
            else:
                computed_unmatched.add((document, row["start_char"], row["end_char"]))
        per_document.append({
            "document_id": document,
            "canonical_sha256": _sha256(canonical_path),
            "current_canonicalizer_from_raw_sha256": hashlib.sha256(
                recomputed_canonical.encode("utf-8")
            ).hexdigest(),
            "current_canonicalizer_matches_pinned_source": source_parity,
            "source_difference_operations": source_difference_operations,
            "gold_exact_spans_intersecting_source_differences": gold_intersecting_source_differences,
            "gold_segment_count": len(all_segments),
            "gold_uncovered_whitespace_chars": sum(end - start for start, end in gap_ranges),
            "gold_uncovered_non_whitespace_chars": 0,
            "gold_overlap_count": 0,
            "gold_exact_spans": len(gold),
            "predicted_spans": len(predicted),
            "matched": len(pairs),
            "gold_unmatched": len(gold) - len(pairs),
            "predicted_unmatched": len(predicted) - len(pairs),
            "prediction_quote_exact": exact_quotes,
            "prediction_quote_whitespace_only": whitespace_only,
        })
        total_exact_quotes += exact_quotes
        total_whitespace_only += whitespace_only
        total_gold += len(gold)
        total_predicted += len(predicted)
        total_matches += len(pairs)

    claimed = {(row["contract_id"], row["gold_start"], row["gold_end"]) for row in claimed_unmatched}
    if len(claimed) != len(claimed_unmatched) or claimed != computed_unmatched:
        raise ValueError("supplied unmatched list differs from independently computed geometry")
    lookup = {(row["contract_id"], row["clause_id"]): row for row in predictions}
    geometry: Counter[str] = Counter()
    for row in claimed_unmatched:
        pred = lookup[(row["contract_id"], row["overlapping_clause_id"])]
        gold_start, gold_end = row["gold_start"], row["gold_end"]
        pred_start, pred_end = pred["start_char"], pred["end_char"]
        if pred_start <= gold_start and gold_end <= pred_end:
            geometry["gold_inside_prediction"] += 1
        elif gold_start <= pred_start and pred_end <= gold_end:
            geometry["prediction_inside_gold"] += 1
        else:
            geometry["partial_crossing"] += 1

    ceiling_by_label = {
        label: 2 * matched_support[label] / (support[label] + matched_support[label])
        for label in sorted(support)
    }
    result = {
        "scope": "D1 HDLD001-004; geometric audit only, no Gemini inference or M7 rescore",
        "input_sha256": {
            "saved_198_clauses": _sha256(predictions_path),
            "saved_63_unmatched": _sha256(unmatched_path),
            "saved_report": _sha256(report_path),
            "clauses_v06": _sha256(data_root / "data/processed/clauses_v06.csv"),
        },
        "per_document": per_document,
        "totals": {
            "gold_exact_spans": total_gold,
            "predicted_spans": total_predicted,
            "matched": total_matches,
            "gold_unmatched": total_gold - total_matches,
            "predicted_unmatched": total_predicted - total_matches,
            "prediction_quote_exact": total_exact_quotes,
            "prediction_quote_whitespace_only": total_whitespace_only,
            "unmatched_list_exactly_reproduced": True,
            "unmatched_geometry": dict(sorted(geometry.items())),
            "current_canonicalizer_source_parity_documents": source_parity_count,
        },
        "optimistic_m7_macro_f1_ceiling_ignoring_false_positives": (
            sum(ceiling_by_label.values()) / len(ceiling_by_label)
        ),
        "ceiling_note": (
            "Assumes every matched prediction has the correct label and ignores all false positives; "
            "not an achieved M7 score."
        ),
        "reported_preliminary_m7": original_report["m7_preliminary"]["macro_f1"],
        "new_m7_score": None,
        "new_m7_score_reason": "The supplied 198-clause artifact has no per-clause predicted labels.",
        "source_parity_note": (
            "The pinned Gold source hash matches its saved canonical file, but current canonicalize(raw_text) "
            "must be compared separately before claiming a shared coordinate source."
        ),
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--unmatched", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.data_root, args.predictions, args.unmatched, args.report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["totals"], ensure_ascii=False))


if __name__ == "__main__":
    main()
