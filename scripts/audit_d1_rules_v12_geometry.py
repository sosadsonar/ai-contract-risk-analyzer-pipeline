"""Measure rules_v1.2 D1 Dev span geometry without classifying or changing Gold."""

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from app.clause.segmenter import SEGMENTATION_VERSION, segment
from app.privacy.masker import mask

from ai_pipeline.evaluation.metrics.alignment import greedy_align_spans

DOCS = ("HDLD001", "HDLD002", "HDLD003", "HDLD004")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def measure(text: str, gold_json: dict, exact_ids: set[str], labels: dict[str, str]) -> dict:
    masked = mask(text)
    predicted = segment(text, masked.masked_text, masked.pii_spans).clauses
    gold = [row for row in gold_json["segments"] if row["gold_clause_ref"] in exact_ids]
    pairs = greedy_align_spans(
        [(row["start_char"], row["end_char"]) for row in gold],
        [(row.start_char, row.end_char) for row in predicted],
    )
    support = Counter(labels[row["gold_clause_ref"]] for row in gold)
    matched = Counter(labels[gold[gold_index]["gold_clause_ref"]] for gold_index, _ in pairs)
    eligible_labels = [label for label, count in support.items() if count >= 5]
    ceiling = sum(2 * matched[label] / (support[label] + matched[label]) for label in eligible_labels)
    ceiling /= len(eligible_labels)
    return {
        "gold_exact": len(gold),
        "predicted": len(predicted),
        "matched_iou_0_5": len(pairs),
        "gold_unmatched": len(gold) - len(pairs),
        "predicted_unmatched": len(predicted) - len(pairs),
        "masker_span_count": len(masked.pii_spans),
        "optimistic_macro_ceiling_ignoring_false_positives": ceiling,
        "gold_support_by_label": dict(sorted(support.items())),
        "matched_support_by_label": dict(sorted(matched.items())),
    }


def audit(data_root: Path) -> dict:
    with (data_root / "data/processed/clauses_v06.csv").open(encoding="utf-8-sig", newline="") as stream:
        exact_ids = {row["clause_id"] for row in csv.DictReader(stream) if row["offset_quality"] == "EXACT"}
    restricted = data_root / "data/intake/restricted"
    private = data_root / "data/intake/private/D1_m1_pipeline_canonical_candidate_v01"
    documents = []
    for doc in DOCS:
        old_text_path = restricted / "D1_m1_runtime_predictions_v01" / f"{doc}.canonical_nfc.txt"
        old_gold_path = restricted / "D1_m1_gold_v01" / f"{doc}.gold_segmentation.json"
        new_text_path = private / f"{doc}.pipeline_canonical.txt"
        candidate_path = private / f"{doc}.candidate_segmentation.json"
        old_text = old_text_path.read_text(encoding="utf-8")
        old_gold = json.loads(old_gold_path.read_text(encoding="utf-8"))
        new_text = new_text_path.read_text(encoding="utf-8")
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        label_path = restricted / "D1_clause_label_gold_v01" / f"{doc}.gold_clause_labels.json"
        labels = {row["clause_id"]: row["labels"][0]
                  for row in json.loads(label_path.read_text(encoding="utf-8"))["items"]}
        if old_gold["source_sha256"] != digest(old_text_path) or candidate["source_sha256"] != digest(new_text_path):
            raise ValueError(f"source hash mismatch: {doc}")
        if candidate["status"] != "AI_CANDIDATE_NEEDS_REVIEW":
            raise ValueError(f"candidate unexpectedly approved: {doc}")
        documents.append({
            "document_id": doc,
            "locked_nfc": {"source_sha256": digest(old_text_path), **measure(old_text, old_gold, exact_ids, labels)},
            "pipeline_canonical_candidate": {
                "source_sha256": digest(new_text_path), **measure(new_text, candidate, exact_ids, labels),
            },
        })
    support = Counter()
    matched = Counter()
    for row in documents:
        support.update(row["locked_nfc"]["gold_support_by_label"])
        matched.update(row["locked_nfc"]["matched_support_by_label"])
    eligible_labels = [label for label, count in support.items() if count >= 5]
    overall_ceiling = sum(2 * matched[label] / (support[label] + matched[label]) for label in eligible_labels)
    overall_ceiling /= len(eligible_labels)
    return {
        "status": "GEOMETRY_ONLY_NO_M7_SCORE",
        "segmentation_version": SEGMENTATION_VERSION,
        "documents": documents,
        "locked_nfc_total_matches": sum(row["locked_nfc"]["matched_iou_0_5"] for row in documents),
        "candidate_total_matches": sum(row["pipeline_canonical_candidate"]["matched_iou_0_5"] for row in documents),
        "optimistic_macro_ceiling_ignoring_false_positives": overall_ceiling,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.data_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "version": result["segmentation_version"],
        "locked_nfc_matches": result["locked_nfc_total_matches"],
        "candidate_matches": result["candidate_total_matches"],
    }))


if __name__ == "__main__":
    main()
