"""Validate the private D1 canonical candidate and emit text-free M7 review metadata."""

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

from app.document.canonicalizer import canonicalize

from ai_pipeline.evaluation.metrics.alignment import greedy_align_spans

DOCS = ("HDLD001", "HDLD002", "HDLD003", "HDLD004")
PREDICTION_SHA256 = {
    "HDLD001": "5221d5ae6bc18bddbffea7b800fd3e9ff9f3f3923b2453a94da712e92efbb338",
    "HDLD002": "b829292c1bb17c3c3ae179e33301af5d9cfac43604da2440c509da4d011beb70",
    "HDLD003": "88fad6bad1743ce0e0107f6515bf5f2bc75e9c2347e0e2c25501e65e04429eee",
    "HDLD004": "bacfc26b0442c1b359bff9814a704483497f5b1435a0b8f34f338c4c1639c31c",
}
BOUNDARIES_SHA256 = "58f8e0b2567f53b80cbe6788ce6a297a43e88bc981b3e7020bae68056b78db2b"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def normalized_slice(text: str, start: int, end: int) -> str:
    return re.sub(r"\s+", " ", text[start:end]).strip()


def audit(data_root: Path, unmatched_path: Path, score_path: Path, boundaries_path: Path) -> dict:
    candidate_root = data_root / "data/intake/private/D1_m1_pipeline_canonical_candidate_v01"
    gold_root = data_root / "data/intake/restricted/D1_m1_gold_v01"
    with (data_root / "data/processed/clauses_v06.csv").open(encoding="utf-8-sig", newline="") as stream:
        exact_refs = {r["clause_id"] for r in csv.DictReader(stream) if r["offset_quality"] == "EXACT"}
    unmatched = read(unmatched_path)
    score = read(score_path)
    if sha(boundaries_path) != BOUNDARIES_SHA256:
        raise ValueError("saved boundary hash mismatch")
    boundaries = read(boundaries_path)
    if len(boundaries) != 198:
        raise ValueError("saved boundary count changed")
    manifest = read(candidate_root / "manifest.json")
    if manifest["status"] != "AI_CANDIDATE_NEEDS_REVIEW":
        raise ValueError("candidate status changed")
    rows = []
    prediction_rows = []
    expected_unmatched = {(r["contract_id"], r["gold_start"], r["gold_end"]) for r in unmatched}
    if len(expected_unmatched) != len(unmatched):
        raise ValueError("duplicate supplied unmatched span")
    seen_unmatched = set()
    documents = []
    totals = Counter()
    for document in DOCS:
        record = next(r for r in manifest["documents"] if r["document_id"] == document)
        text_path = candidate_root / f"{document}.pipeline_canonical.txt"
        candidate_path = candidate_root / f"{document}.candidate_segmentation.json"
        prediction_path = candidate_root / f"{document}.candidate_prediction_offsets.json"
        old_gold_path = gold_root / f"{document}.gold_segmentation.json"
        old_text_path = (data_root / "data/intake/restricted/D1_m1_runtime_predictions_v01"
                         / f"{document}.canonical_nfc.txt")
        raw_path = data_root / "data/processed/raw_text" / f"{document}.txt"
        text = text_path.read_text(encoding="utf-8")
        candidate = read(candidate_path)
        predictions = read(prediction_path)
        old_gold = read(old_gold_path)
        original_prediction_text = old_text_path.read_text(encoding="utf-8")
        raw = raw_path.read_text(encoding="utf-8")
        if (sha(prediction_path) != PREDICTION_SHA256[document]
                or sha(text_path) != record["pipeline_canonical_sha256"]
                or sha(candidate_path) != record["candidate_sha256"]
                or sha(old_gold_path) != record["old_gold_sha256"]
                or sha(raw_path) != record["source_raw_sha256"]
                or candidate["source_sha256"] != sha(text_path)):
            raise ValueError(f"source or candidate hash mismatch: {document}")
        if text != canonicalize([raw]) or old_gold["source_sha256"] != hashlib.sha256(
            unicodedata.normalize("NFC", raw).encode("utf-8")
        ).hexdigest():
            raise ValueError(f"canonical policy mismatch: {document}")
        spans = sorted(candidate["segments"], key=lambda r: r["start_char"])
        old_by_ref = {r["gold_clause_ref"]: r for r in old_gold["segments"]}
        if not spans or len(old_by_ref) != len(spans) or {r["gold_clause_ref"] for r in spans} != set(old_by_ref):
            raise ValueError(f"missing or duplicate segment: {document}")
        covered = bytearray(len(text))
        for span in spans:
            start, end = span["start_char"], span["end_char"]
            if not 0 <= start < end <= len(text) or any(covered[start:end]):
                raise ValueError(f"invalid or overlapping span: {document}")
            covered[start:end] = b"\x01" * (end - start)
            if not text[start:end].strip():
                raise ValueError(f"blank segment: {document}")
            old = old_by_ref[span["gold_clause_ref"]]
            gold_text = unicodedata.normalize("NFC", raw)[old["start_char"]:old["end_char"]]
            if re.sub(r"\s+", " ", gold_text).strip() != normalized_slice(text, start, end):
                raise ValueError(f"rebased quote differs: {document}/{span['gold_clause_ref']}")
        nonwhite_gap = sum(not char.isspace() and not covered[i] for i, char in enumerate(text))
        if nonwhite_gap:
            raise ValueError(f"non-whitespace coverage gap: {document}")
        for pred in predictions:
            if not 0 <= pred["start_char"] < pred["end_char"] <= len(text):
                raise ValueError(f"prediction offset outside canonical text: {document}")
        source_predictions = [r for r in boundaries if r["contract_id"] == document]
        if (sha(old_text_path) != old_gold["source_sha256"]
                or len(source_predictions) != len(predictions)
                or len({r["clause_id"] for r in predictions}) != len(predictions)):
            raise ValueError(f"saved prediction source or count mismatch: {document}")
        for source_pred, pred in zip(source_predictions, predictions):
            if (source_pred["contract_id"] != pred["contract_id"]
                    or source_pred["clause_id"] != pred["clause_id"]
                    or not 0 <= source_pred["start_char"] < source_pred["end_char"] <= len(original_prediction_text)
                    or normalized_slice(original_prediction_text, source_pred["start_char"], source_pred["end_char"])
                    != normalized_slice(text, pred["start_char"], pred["end_char"])):
                raise ValueError(f"saved prediction rebase mismatch: {document}")
        eligible = [r for r in spans if r["gold_clause_ref"] in exact_refs]
        pairs = greedy_align_spans(
            [(r["start_char"], r["end_char"]) for r in eligible],
            [(r["start_char"], r["end_char"]) for r in predictions],
        )
        missed = {i for i in range(len(eligible))} - {i for i, _ in pairs}
        unmatched_predictions = {i for i in range(len(predictions))} - {i for _, i in pairs}
        score_doc = next(r for r in score["per_document"] if r["document_id"] == document)
        if len(missed) != score_doc["gold_exact"] - score_doc["official_greedy_matches"]:
            raise ValueError(f"official geometry count changed: {document}")
        context = [r for r in spans if r["gold_clause_ref"] not in exact_refs]
        for index in sorted(unmatched_predictions):
            pred = predictions[index]
            def intersects(row: dict) -> bool:
                return min(pred["end_char"], row["end_char"]) > max(pred["start_char"], row["start_char"])
            prediction_rows.append({
                "document_id": document,
                "prediction_id": pred["clause_id"],
                "start_char": pred["start_char"],
                "end_char": pred["end_char"],
                "overlaps_exact_gold": any(intersects(row) for row in eligible),
                "overlaps_context_gold": any(intersects(row) for row in context),
            })
        for index in sorted(missed):
            gold = eligible[index]
            old = old_by_ref[gold["gold_clause_ref"]]
            seen_unmatched.add((document, old["start_char"], old["end_char"]))
            overlaps = []
            for pred in predictions:
                overlap = max(0, min(gold["end_char"], pred["end_char"]) - max(gold["start_char"], pred["start_char"]))
                if overlap:
                    union = max(gold["end_char"], pred["end_char"]) - min(gold["start_char"], pred["start_char"])
                    overlaps.append((overlap / union, pred))
            if not overlaps:
                relation, best_iou, pred = "no_overlap", 0, None
            else:
                best_iou, pred = max(overlaps, key=lambda item: item[0])
                if pred["start_char"] <= gold["start_char"] and gold["end_char"] <= pred["end_char"]:
                    relation = "gold_inside_prediction"
                elif gold["start_char"] <= pred["start_char"] and pred["end_char"] <= gold["end_char"]:
                    relation = "prediction_inside_gold"
                else:
                    relation = "partial_crossing"
            rows.append({
                "document_id": document,
                "gold_ref": gold["gold_clause_ref"],
                "gold_start": gold["start_char"],
                "gold_end": gold["end_char"],
                "best_prediction_id": pred["clause_id"] if pred else None,
                "best_iou": round(best_iou, 6),
                "relation": relation,
                "prediction_contains_multiple_gold": sum(
                    pred["start_char"] <= other["start_char"] and other["end_char"] <= pred["end_char"]
                    for other in eligible
                ) > 1 if pred else False,
            })
            totals[relation] += 1
        documents.append({
            "document_id": document,
            "canonical_sha256": sha(text_path),
            "candidate_sha256": sha(candidate_path),
            "prediction_sha256": sha(prediction_path),
            "segments": len(spans),
            "exact_gold": len(eligible),
            "predicted": len(predictions),
            "official_matches": len(pairs),
            "uncovered_non_whitespace": nonwhite_gap,
            "uncovered_whitespace": sum(char.isspace() and not covered[i] for i, char in enumerate(text)),
        })
    if len(rows) != 63:
        raise ValueError("unexpected unmatched count")
    if len(prediction_rows) != 87:
        raise ValueError("unexpected unmatched prediction count")
    if seen_unmatched != expected_unmatched:
        raise ValueError("supplied unmatched list differs from canonical candidate")
    return {
        "status": "CANONICAL_REBASE_AUDIT_ONLY_NOT_GOLD",
        "candidate_manifest_sha256": sha(candidate_root / "manifest.json"),
        "unmatched_input_sha256": sha(unmatched_path),
        "score_input_sha256": sha(score_path),
        "boundaries_input_sha256": sha(boundaries_path),
        "documents": documents,
        "unmatched_totals": dict(totals),
        "unmatched_review_rows": rows,
        "unmatched_prediction_review_rows": prediction_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--unmatched", type=Path, required=True)
    parser.add_argument("--score", type=Path, required=True)
    parser.add_argument("--boundaries", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.data_root, args.unmatched, args.score, args.boundaries)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "documents": len(result["documents"]),
        "unmatched": len(result["unmatched_review_rows"]),
        "relations": result["unmatched_totals"],
    }))


if __name__ == "__main__":
    main()
