"""Rebase adjudicated D1 M1 coordinates into pipeline canonical text as a private candidate."""

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from pathlib import Path

from app.document.canonicalizer import canonicalize

from ai_pipeline.evaluation.d1_clause_run import offset_mapper
from ai_pipeline.evaluation.metrics.alignment import greedy_align_spans

DOCUMENTS = ("HDLD001", "HDLD002", "HDLD003", "HDLD004")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized_quote(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def build(data_root: Path, output: Path, predictions_path: Path | None = None) -> dict:
    """Write review-only artifacts; never alter adjudicated Gold or its source files."""
    gold_root = data_root / "data/intake/restricted/D1_m1_gold_v01"
    raw_root = data_root / "data/processed/raw_text"
    output.mkdir(parents=True, exist_ok=True)
    predictions = json.loads(predictions_path.read_text(encoding="utf-8")) if predictions_path else None
    with (data_root / "data/processed/clauses_v06.csv").open(encoding="utf-8-sig", newline="") as stream:
        exact_ids = {row["clause_id"] for row in csv.DictReader(stream) if row["offset_quality"] == "EXACT"}
    rows = []
    for document in DOCUMENTS:
        raw_path = raw_root / f"{document}.txt"
        gold_path = gold_root / f"{document}.gold_segmentation.json"
        raw = raw_path.read_text(encoding="utf-8")
        old_canonical = unicodedata.normalize("NFC", raw)
        new_canonical = canonicalize([raw])
        gold = json.loads(gold_path.read_text(encoding="utf-8"))
        if digest(old_canonical.encode("utf-8")) != gold["source_sha256"]:
            raise ValueError(f"Gold source is not NFC raw text: {document}")
        mapping = offset_mapper(old_canonical, new_canonical)
        candidate_segments = []
        review_refs = []
        exact_count = 0
        for segment in gold["segments"]:
            start, end = segment["start_char"], segment["end_char"]
            new_start, new_end = mapping(start), mapping(end)
            if not 0 <= new_start < new_end <= len(new_canonical):
                raise ValueError(f"invalid rebased span: {document}/{segment['gold_clause_ref']}")
            equivalent = normalized_quote(old_canonical[start:end]) == normalized_quote(
                new_canonical[new_start:new_end]
            )
            if equivalent:
                exact_count += 1
            else:
                review_refs.append(segment["gold_clause_ref"])
            candidate_segments.append({**segment, "start_char": new_start, "end_char": new_end})
        ordered = sorted(candidate_segments, key=lambda item: item["start_char"])
        if any(a["end_char"] > b["start_char"] for a, b in zip(ordered, ordered[1:])):
            raise ValueError(f"rebased spans overlap: {document}")
        candidate = {
            **gold,
            "status": "AI_CANDIDATE_NEEDS_REVIEW",
            "source_sha256": digest(new_canonical.encode("utf-8")),
            "derived_from_gold_sha256": digest(gold_path.read_bytes()),
            "segments": candidate_segments,
        }
        canonical_path = output / f"{document}.pipeline_canonical.txt"
        candidate_path = output / f"{document}.candidate_segmentation.json"
        canonical_path.write_bytes(new_canonical.encode("utf-8"))
        candidate_path.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        record = {
            "document_id": document,
            "source_raw_sha256": digest(raw_path.read_bytes()),
            "old_gold_sha256": digest(gold_path.read_bytes()),
            "pipeline_canonical_sha256": candidate["source_sha256"],
            "candidate_sha256": digest(candidate_path.read_bytes()),
            "segments": len(candidate_segments),
            "quote_equivalent_after_whitespace_normalization": exact_count,
            "needs_manual_review_refs": review_refs,
        }
        if predictions is not None:
            document_predictions = [row for row in predictions if row["contract_id"] == document]
            rebased_predictions = []
            prediction_review_refs = []
            for prediction in document_predictions:
                start = mapping(prediction["start_char"])
                end = mapping(prediction["end_char"])
                if not 0 <= start < end <= len(new_canonical):
                    raise ValueError(f"invalid rebased prediction: {document}/{prediction['clause_id']}")
                if normalized_quote(prediction["text"]) != normalized_quote(new_canonical[start:end]):
                    prediction_review_refs.append(prediction["clause_id"])
                rebased_predictions.append({
                    "clause_id": prediction["clause_id"],
                    "contract_id": document,
                    "start_char": start,
                    "end_char": end,
                })
            eligible_gold = [
                (item["start_char"], item["end_char"])
                for item in candidate_segments
                if item["gold_clause_ref"] in exact_ids
            ]
            prediction_spans = [(item["start_char"], item["end_char"]) for item in rebased_predictions]
            record["rebased_prediction_count"] = len(rebased_predictions)
            record["rebased_prediction_review_refs"] = prediction_review_refs
            record["rebased_exact_gold_count"] = len(eligible_gold)
            record["rebased_geometry_matches_at_iou_0_5"] = len(
                greedy_align_spans(eligible_gold, prediction_spans)
            )
            (output / f"{document}.candidate_prediction_offsets.json").write_text(
                json.dumps(rebased_predictions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        rows.append(record)
    manifest = {
        "status": "AI_CANDIDATE_NEEDS_REVIEW",
        "scope": "D1 HDLD001-004 M1 coordinate rebase only; original Gold unchanged",
        "documents": rows,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--predictions", type=Path)
    args = parser.parse_args()
    result = build(args.data_root, args.output, args.predictions)
    print(json.dumps({
        "status": result["status"],
        "segments": sum(row["segments"] for row in result["documents"]),
        "quote_equivalent": sum(row["quote_equivalent_after_whitespace_normalization"] for row in result["documents"]),
        "needs_review": sum(len(row["needs_manual_review_refs"]) for row in result["documents"]),
    }))


if __name__ == "__main__":
    main()
