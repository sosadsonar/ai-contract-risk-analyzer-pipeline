"""Compare one parser build with D2 Dev Gold geometry without exporting source text."""

import argparse
import hashlib
import json
from pathlib import Path

from app.clause import segmenter
from app.clause.structure_parser import STRUCTURE_PARSER_VERSION
from app.privacy.masker import mask

from ai_pipeline.evaluation.metrics.alignment import greedy_align_spans

DOCUMENTS = ("HDLD001", "HDLD002", "HDLD003", "HDLD004")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(data_root: Path, expected_version: str, enable_plus_lists: bool = False) -> dict:
    effective_version = (getattr(segmenter, "PLUS_SEGMENTATION_VERSION", "rules_v1.2")
                         if enable_plus_lists else segmenter.SEGMENTATION_VERSION)
    if effective_version != expected_version:
        raise ValueError("unexpected segmenter version")
    restricted = data_root / "data/intake/restricted"
    rows = []
    for document in DOCUMENTS:
        text_path = restricted / "D2_candidate_v02" / f"{document}.d2_candidate.txt"
        gold_path = restricted / "D2_segmentation_gold_v01" / f"{document}.gold_segmentation.json"
        text = text_path.read_text(encoding="utf-8")
        gold = json.loads(gold_path.read_text(encoding="utf-8"))
        if gold["status"] != "GOLD_ADJUDICATED" or gold["source_sha256"] != sha(text_path):
            raise ValueError(f"D2 source/Gold mismatch: {document}")
        gold_spans = [(r["start_char"], r["end_char"]) for r in gold["segments"]]
        masked = mask(text)
        if enable_plus_lists:
            predicted = segmenter.segment(text, masked.masked_text, masked.pii_spans, enable_plus_lists=True).clauses
        else:
            predicted = segmenter.segment(text, masked.masked_text, masked.pii_spans).clauses
        predicted_spans = [(r.start_char, r.end_char) for r in predicted]
        matches = greedy_align_spans(gold_spans, predicted_spans, threshold=0.5)
        matched_gold = {gold_index for gold_index, _ in matches}
        rows.append({
            "document_id": document,
            "source_sha256": sha(text_path),
            "gold_sha256": sha(gold_path),
            "gold_count": len(gold_spans),
            "predicted_count": len(predicted_spans),
            "matched_iou_0_5": len(matches),
            "gold_unmatched": len(gold_spans) - len(matches),
            "prediction_unmatched": len(predicted_spans) - len(matches),
            "unmatched_gold": [
                {"gold_ref": row["gold_clause_ref"], "start_char": row["start_char"], "end_char": row["end_char"]}
                for index, row in enumerate(gold["segments"]) if index not in matched_gold
            ],
        })
    return {
        "status": "D2_DEV_GEOMETRY_ONLY_NO_CLASSIFICATION_SCORE",
        "segmentation_version": effective_version,
        "structure_parser_version": STRUCTURE_PARSER_VERSION,
        "documents": rows,
        "totals": {
            key: sum(row[key] for row in rows)
            for key in ("gold_count", "predicted_count", "matched_iou_0_5", "gold_unmatched", "prediction_unmatched")
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--enable-plus-lists", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.data_root, args.expected_version, args.enable_plus_lists)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["totals"]))


if __name__ == "__main__":
    main()
