"""Score saved D1 predicted labels offline against adjudicated, EXACT Gold spans."""

import argparse
import csv
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

from ai_pipeline.evaluation.metrics.alignment import diagnose_span_alignment
from ai_pipeline.evaluation.metrics.clause_classification import (
    GoldSpan,
    PredClause,
    evaluate_clause_classification,
)

DOCUMENTS = ("HDLD001", "HDLD002", "HDLD003", "HDLD004")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prediction_labels(record: dict) -> tuple[str, ...]:
    labels = record.get("clause_labels", record.get("labels", record.get("label")))
    if isinstance(labels, str):
        labels = [labels]
    if not isinstance(labels, list) or not 1 <= len(labels) <= 3 or any(
        not isinstance(label, str) or not label for label in labels
    ):
        raise ValueError("each prediction must have one to three non-empty clause labels")
    return tuple(labels)


def macro_from_results(results: list[dict], *, min_support: int = 5) -> float | None:
    counts: dict[str, Counter] = {}
    for result in results:
        for label, row in result["per_label"].items():
            if label not in counts:
                counts[label] = Counter()
            counts[label].update({key: row[key] for key in ("support", "tp", "fp", "fn")})
    scores = []
    for row in counts.values():
        if row["support"] < min_support:
            continue
        denominator = 2 * row["tp"] + row["fp"] + row["fn"]
        scores.append(2 * row["tp"] / denominator if denominator else 0.0)
    return sum(scores) / len(scores) if scores else None


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[min(lower + 1, len(ordered) - 1)] * fraction


def score(data_root: Path, boundaries_path: Path, labels_path: Path, *, resamples: int = 1000, seed: int = 0) -> dict:
    """Require one labeled record per saved prediction and preserve document clusters."""
    restricted = data_root / "data/intake/restricted"
    boundaries = json.loads(boundaries_path.read_text(encoding="utf-8"))
    supplied = json.loads(labels_path.read_text(encoding="utf-8"))
    if not isinstance(boundaries, list) or not isinstance(supplied, list):
        raise ValueError("boundaries and labels must be JSON arrays")
    boundary_keys = [(row["contract_id"], row["clause_id"]) for row in boundaries]
    label_keys = [(row["contract_id"], row["clause_id"]) for row in supplied]
    if len(boundary_keys) != 198 or len(set(boundary_keys)) != 198 or set(label_keys) != set(boundary_keys):
        raise ValueError("labeled file must cover exactly the 198 saved D1 clause IDs")
    if len(label_keys) != 198 or len(set(label_keys)) != 198:
        raise ValueError("duplicate labeled prediction IDs")
    if {document for document, _ in boundary_keys} != set(DOCUMENTS):
        raise ValueError("only D1 HDLD001-004 may be scored")
    by_key = {(row["contract_id"], row["clause_id"]): prediction_labels(row) for row in supplied}
    with (data_root / "data/processed/clauses_v06.csv").open(encoding="utf-8-sig", newline="") as stream:
        exact_ids = {row["clause_id"] for row in csv.DictReader(stream) if row["offset_quality"] == "EXACT"}
    per_document = []
    confusion = []
    for document in DOCUMENTS:
        canonical_path = restricted / "D1_m1_runtime_predictions_v01" / f"{document}.canonical_nfc.txt"
        gold_path = restricted / "D1_m1_gold_v01" / f"{document}.gold_segmentation.json"
        labels_gold_path = restricted / "D1_clause_label_gold_v01" / f"{document}.gold_clause_labels.json"
        canonical = canonical_path.read_text(encoding="utf-8")
        gold_json = json.loads(gold_path.read_text(encoding="utf-8"))
        if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != gold_json["source_sha256"]:
            raise ValueError(f"Gold source hash mismatch: {document}")
        gold_labels = {
            row["clause_id"]: row["labels"]
            for row in json.loads(labels_gold_path.read_text(encoding="utf-8"))["items"]
        }
        gold = []
        for segment in gold_json["segments"]:
            ref = segment["gold_clause_ref"]
            if ref in exact_ids:
                labels = gold_labels[ref]
                if len(labels) != 1:
                    raise ValueError("M7 offline scorer requires one Gold label per EXACT span")
                gold.append(GoldSpan(segment["start_char"], segment["end_char"], labels[0]))
        pred_rows = [row for row in boundaries if row["contract_id"] == document]
        pred = [
            PredClause(row["start_char"], row["end_char"], by_key[(document, row["clause_id"])])
            for row in pred_rows
        ]
        result = evaluate_clause_classification(gold, pred, min_support=1)
        diagnostics = diagnose_span_alignment(
            [(row.start, row.end) for row in gold],
            [(row.start, row.end) for row in pred],
            text=canonical,
        )
        confusion.append(result)
        per_document.append({
            "document_id": document,
            "canonical_sha256": digest(canonical_path),
            "gold_exact": len(gold),
            "predicted": len(pred),
            "official_greedy_matches": result["aligned"],
            "diagnostic_containment_matches": len(diagnostics["containment_pairs"]),
        })
    main_score = macro_from_results(confusion)
    rng = random.Random(seed)
    bootstrap = [
        macro_from_results([confusion[rng.randrange(len(confusion))] for _ in DOCUMENTS])
        for _ in range(resamples)
    ]
    numeric = [value for value in bootstrap if value is not None]
    return {
        "status": "OFFLINE_SCORE_ON_PINNED_NFC_GOLD",
        "metric": "M7_Macro_F1",
        "official_greedy_iou_threshold": 0.5,
        "macro_f1": main_score,
        "bootstrap_95_ci": [percentile(numeric, 0.025), percentile(numeric, 0.975)] if numeric else None,
        "bootstrap_resamples": resamples,
        "bootstrap_seed": seed,
        "document_cluster_count": len(DOCUMENTS),
        "diagnostic_containment_is_not_official_score": True,
        "per_document": per_document,
        "input_sha256": {"boundaries": digest(boundaries_path), "predicted_labels": digest(labels_path)},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--boundaries", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = score(args.data_root, args.boundaries, args.labels)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"macro_f1": result["macro_f1"], "bootstrap_95_ci": result["bootstrap_95_ci"]}))


if __name__ == "__main__":
    main()
