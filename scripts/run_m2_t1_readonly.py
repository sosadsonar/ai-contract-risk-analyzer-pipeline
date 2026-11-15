"""One-shot T1 closed-corpus M2 diagnostic with frozen Dev rules.

The caller must invoke this once after freezing the baseline. No contract text,
PII, or clause labels are written to the report or stdout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import unicodedata
from pathlib import Path

from app.privacy.masker import mask
from app.risk.dev_m2_baseline import detect_dev_m2_risks

from ai_pipeline.evaluation.metrics.risk_classification import (
    RiskRecord,
    evaluate_risk_classification,
)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(data_root: Path) -> dict:
    restricted = data_root / "data/intake/restricted"
    gold_root = restricted / "T1_m2_risk_gold_v02"
    manifest = _read_json(gold_root / "manifest.json")
    if (manifest["status"] != "GOLD_ADJUDICATED_CLOSED_CORPUS_V1"
            or manifest["evaluation_ready"] is not True
            or manifest["scope_counts"] != {
                "IN_CORPUS_VERIFIED": 1474,
                "CORPUS_V1_SCOPE_EXCEPTION": 17,
                "IN_CORPUS_ADJUDICATED": 3,
            }):
        raise ValueError("T1 closed-corpus review status changed")
    if len(manifest["excluded_corpus_scope_unit_ids"]) != 17:
        raise ValueError("T1 excluded scope inventory changed")
    context_ids = set(manifest["context_scope_unit_ids"])
    excluded_ids = set(manifest["excluded_corpus_scope_unit_ids"])
    if context_ids & excluded_ids:
        raise ValueError("T1 context and corpus-exception scopes overlap")
    records = []
    gold_records = []
    source_hashes = {}
    candidate_count = 0
    for doc in manifest["documents"]:
        gold = _read_json(gold_root / f"{doc}.risk_gold.json")
        if gold["status"] != "GOLD_ADJUDICATED_CLOSED_CORPUS_V1":
            raise ValueError("T1 risk Gold status changed")
        segmentation = _read_json(restricted / "T1_segmentation_candidate_v01" /
                                  f"{doc}_segments.json")
        raw = (data_root / "data/processed/raw_text" / f"{doc}.txt").read_bytes()
        source = unicodedata.normalize("NFC", raw.decode("utf-8"))
        source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
        if source_hash != segmentation["canonical_text_sha256"]:
            raise ValueError("T1 canonical source hash mismatch")
        source_hashes[doc] = source_hash
        masked = mask(source).masked_text
        candidate_spans = {}
        for item in segmentation["segments"]:
            clause_id = item["candidate_segment_id"]
            start, end = item["start_char"], item["end_char"]
            if not 0 <= start < end <= len(masked):
                raise ValueError("T1 candidate span outside source")
            candidate_spans[clause_id] = (start, end)
            if item["kind"] != "CLAUSE":
                continue
            candidate_count += 1
            for role, label, basis in detect_dev_m2_risks(masked[start:end]):
                if f"{clause_id}::{role}" in context_ids:
                    continue
                records.append(RiskRecord(clause_id, role, label, basis,
                                          start, end, doc))
        for item in gold["items"]:
            clause_id = item["clause_id"]
            unit_id = f"{clause_id}::{item['role']}"
            if unit_id in excluded_ids or unit_id in context_ids:
                raise ValueError("T1 Gold positive appears in excluded scope")
            start, end = item["start_char"], item["end_char"]
            if clause_id not in candidate_spans or not 0 <= start < end <= len(masked):
                raise ValueError("T1 Gold positive lacks a valid candidate span")
            gold_records.append(RiskRecord(clause_id, item["role"],
                                           item["risk_label"], item["basis_type"],
                                           start, end, doc))
    if len(gold_records) != 3 or candidate_count != 747:
        raise ValueError("T1 M2 inventory changed")
    score = evaluate_risk_classification(
        gold_records, records, require_gold_spans=True,
        excluded_scope_regions=manifest["excluded_corpus_scope_regions"],
    )
    return {
        "status": "ONE_SHOT_T1_CLOSED_CORPUS_READONLY",
        "gold_version": "T1_m2_risk_gold_v02",
        "prediction_basis": "T1_segmentation_candidate_v01 plus frozen Dev risk baseline",
        "source_sha256_by_document": source_hashes,
        "gold_positive_count": len(gold_records),
        "candidate_clause_count": candidate_count,
        "context_scope_unit_count": len(context_ids),
        "excluded_corpus_scope_unit_count": len(excluded_ids),
        "score": score,
        "limitations": [
            "Only three adjudicated T1 positives cover two risk labels; not full 21-label M2 acceptance.",
            "T1 segmentation candidates are AI-proposed inputs, not Gold boundaries.",
            "The detector is a frozen Dev heuristic, not the product risk classifier.",
            "CONTEXT scope units are segmentation-only and absent from the M2 packet.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("T1 one-shot output already exists")
    result = evaluate(args.data_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    counts = result["score"]["micro_counts"]
    print(json.dumps({"gold_positive_count": result["gold_positive_count"],
                      "tp": counts["tp"], "fp": counts["fp"], "fn": counts["fn"]}))


if __name__ == "__main__":
    main()
