"""Compare source-only split rules on saved D1 spans; labels are inherited for diagnosis only."""

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from app.clause.structure_parser import parse_structure

from ai_pipeline.evaluation.metrics.clause_classification import (
    GoldSpan,
    PredClause,
    evaluate_clause_classification,
)
from scripts.score_d1_saved_labels_offline import DOCUMENTS, macro_from_results, prediction_labels

RULES = {
    "saved": None,
    "saved_post_article_only": None,
    "plus_each_line": re.compile(r"(?m)^[ \t]*\+[ \t]+"),
    "plus_each_line_post_article_only": re.compile(r"(?m)^[ \t]*\+[ \t]+"),
    "all_list_markers": re.compile(r"(?m)^[ \t]*(?:\+|[-–•]|[a-zA-ZđĐ][.)])[ \t]+"),
    "nonblank_lines": re.compile(r"\n[ \t]*(?=\S)"),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def split_span(text: str, start: int, end: int, rule: re.Pattern[str] | None) -> list[tuple[int, int]]:
    if rule is None:
        return [(start, end)]
    region = text[start:end]
    cuts = {0, len(region)}
    for match in rule.finditer(region):
        if match.start() > 0:
            cuts.add(match.start())
    ordered = sorted(cuts)
    spans = []
    for left, right in zip(ordered, ordered[1:]):
        while left < right and region[left].isspace():
            left += 1
        while right > left and region[right - 1].isspace():
            right -= 1
        if left < right:
            spans.append((start + left, start + right))
    if not spans:
        raise ValueError("split produced no content")
    return spans


def probe(data_root: Path, boundaries_path: Path, labels_path: Path) -> dict:
    boundaries = json.loads(boundaries_path.read_text(encoding="utf-8"))
    labels = json.loads(labels_path.read_text(encoding="utf-8"))
    if len(boundaries) != 198 or len(labels) != 198:
        raise ValueError("expected 198 saved clauses and labels")
    by_key = {(r["contract_id"], r["clause_id"]): prediction_labels(r) for r in labels}
    if len(by_key) != 198 or set(by_key) != {(r["contract_id"], r["clause_id"]) for r in boundaries}:
        raise ValueError("saved label keys differ from boundary keys")
    with (data_root / "data/processed/clauses_v06.csv").open(encoding="utf-8-sig", newline="") as stream:
        exact_ids = {r["clause_id"] for r in csv.DictReader(stream) if r["offset_quality"] == "EXACT"}
    results = {}
    for rule_name, rule in RULES.items():
        evaluations = []
        per_doc = []
        for doc in DOCUMENTS:
            root = data_root / "data/intake/restricted"
            text = (root / "D1_m1_runtime_predictions_v01" / f"{doc}.canonical_nfc.txt").read_text(encoding="utf-8")
            seg = json.loads((root / "D1_m1_gold_v01" / f"{doc}.gold_segmentation.json").read_text(encoding="utf-8"))
            label_artifact = json.loads(
                (root / "D1_clause_label_gold_v01" / f"{doc}.gold_clause_labels.json").read_text(encoding="utf-8")
            )
            gold_labels = {r["clause_id"]: r["labels"][0] for r in label_artifact["items"]}
            gold = [GoldSpan(r["start_char"], r["end_char"], gold_labels[r["gold_clause_ref"]])
                    for r in seg["segments"] if r["gold_clause_ref"] in exact_ids]
            article_starts = [mark.start for mark in parse_structure(text) if mark.kind == "article"]
            first_article = min(article_starts) if article_starts else None
            prediction = []
            for row in boundaries:
                if row["contract_id"] != doc:
                    continue
                if (rule_name.endswith("post_article_only") and first_article is not None
                        and row["end_char"] <= first_article):
                    continue
                for start, end in split_span(text, row["start_char"], row["end_char"], rule):
                    prediction.append(PredClause(start, end, by_key[(doc, row["clause_id"])]))
            result = evaluate_clause_classification(gold, prediction, min_support=1)
            evaluations.append(result)
            per_doc.append({"document_id": doc, "predicted": len(prediction), "aligned": result["aligned"]})
        label_counts: dict[str, Counter] = {}
        for evaluation in evaluations:
            for label, row in evaluation["per_label"].items():
                label_counts.setdefault(label, Counter()).update(
                    {key: row[key] for key in ("support", "tp", "fp", "fn")}
                )
        results[rule_name] = {
            "diagnostic_macro_f1_with_inherited_labels": macro_from_results(evaluations),
            "predicted_total": sum(r["predicted"] for r in per_doc),
            "aligned_total": sum(r["aligned"] for r in per_doc),
            "per_document": per_doc,
            "per_label_counts": {label: dict(counts) for label, counts in sorted(label_counts.items())},
        }
    return {
        "status": "DIAGNOSTIC_ONLY_NOT_INDEPENDENT_PREDICTIONS",
        "input_sha256": {"boundaries": digest(boundaries_path), "labels": digest(labels_path)},
        "note": "Each child inherits its parent's old labels. This is a boundary probe, not a valid new M7 score.",
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--boundaries", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = probe(args.data_root, args.boundaries, args.labels)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({name: {"aligned": row["aligned_total"], "macro": row["diagnostic_macro_f1_with_inherited_labels"]}
                      for name, row in result["results"].items()}))


if __name__ == "__main__":
    main()
