"""Evaluate approved D1/D2 Dev risk slices; write aggregate metadata only.

The deterministic Article 17 detector is a local diagnostic, not the product M2
classifier. Never use this script on T1/T2 or write clause text to its output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path

from app.clause.segmenter import segment
from app.legal.corpus_loader import load_corpus
from app.privacy.masker import mask
from app.risk.dev_injection_candidate import detect_dev_risks_candidate

from ai_pipeline.evaluation.metrics.risk_classification import (
    RiskRecord,
    evaluate_risk_classification,
    map_dev_candidate_to_risk_labels,
)

_DOCS = tuple(f"HDLD{i:03d}" for i in range(1, 5))
_CITATIONS = {
    "DEPOSIT_DOCUMENT_HELD": ("BLLD2019:art17:cl1", "BLLD2019:art17:cl2"),
    "DISCIPLINE_OBLIGATION": ("BLLD2019:art17:cl3",),
}


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _verified_source(path: Path, segmentation_gold: dict) -> str:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != segmentation_gold["source_sha256"]:
        raise ValueError("Dev source hash does not match segmentation Gold")
    return raw.decode("utf-8")


def gold_from_injections(injections: list[dict], segmentation: list[dict],
                         document_id: str) -> list[RiskRecord]:
    """Implement approved two-role Dev policy using D2 v02 clause boundaries."""
    spans = {item["gold_clause_ref"]: item for item in segmentation}
    result = []
    for item in injections:
        if not item["verification"] or any(
            review["decision"] != "VERIFIED" for review in item["verification"]
        ):
            raise ValueError("D2 injection is not verified")
        clause = spans[item["clause_id"]]
        injected = item["insertion_span"]
        if not (clause["start_char"] <= injected["start_char"] < injected["end_char"]
                <= clause["end_char"]):
            raise ValueError("D2 injection lies outside its v02 Gold clause")
        if item["risk_label"] not in {"DEPOSIT_DOCUMENT_HELD", "EMPLOYEE_OBLIGATIONS_DISCIPLINE"}:
            raise ValueError("D2 Dev risk label outside approved Article 17 slice")
        for role in ("EMPLOYEE", "EMPLOYER"):
            _, label = map_dev_candidate_to_risk_labels(((role, item["risk_label"]),))[0]
            result.append(RiskRecord(item["clause_id"], role, label,
                                     "LEGAL_VIOLATION", clause["start_char"],
                                     clause["end_char"], document_id))
    return result


def evaluate_dev(data_root: Path, corpus_root: Path, *, as_of: date) -> dict:
    restricted = data_root / "data" / "intake" / "restricted"
    corpus = load_corpus(corpus_root)
    if corpus.release_status != "APPROVED":
        raise ValueError("legal corpus is not approved")
    provisions = {p.citation_id: p for p in corpus.provisions}
    all_gold: list[RiskRecord] = []
    all_predicted: list[RiskRecord] = []
    d2_gold: list[RiskRecord] = []
    d2_predicted: list[RiskRecord] = []
    segment_counts = Counter()
    source_hashes = {}
    citation_total = citation_valid = quote_total = quote_valid = 0
    for dataset in ("D1", "D2"):
        for doc in _DOCS:
            folder, suffix, gold_folder = (
                ("D1_m1_runtime_predictions_v01", ".canonical_nfc.txt", "D1_m1_gold_v01")
                if dataset == "D1" else
                ("D2_candidate_v02", ".d2_candidate.txt", "D2_segmentation_gold_v02")
            )
            source_path = restricted / folder / f"{doc}{suffix}"
            geometry = _read_json(restricted / gold_folder / f"{doc}.gold_segmentation.json")
            expected_status = ("GOLD_ADJUDICATED" if dataset == "D1"
                               else "ADJUDICATED_D2_GOLD_V02")
            if geometry["status"] != expected_status:
                raise ValueError("Dev segmentation Gold is not adjudicated")
            source = _verified_source(source_path, geometry)
            source_hashes[f"{dataset}:{doc}"] = geometry["source_sha256"]
            spans = {item["gold_clause_ref"]: item for item in geometry["segments"]}
            doc_id = f"{dataset}:{doc}"
            if dataset == "D1":
                risk_gold = _read_json(restricted / "D1_m2_risk_gold_v02" /
                                       f"{doc}.risk_gold.json")
                if risk_gold["status"] != "GOLD_ADJUDICATED":
                    raise ValueError("D1 risk Gold is not adjudicated")
                for item in risk_gold["items"]:
                    span = spans[item["clause_id"]]
                    all_gold.append(RiskRecord(item["clause_id"], item["role"],
                                               item["risk_label"], item["basis_type"],
                                               span["start_char"], span["end_char"], doc_id))
            else:
                injections = _read_json(restricted / "D2_injection_gold_v01" /
                                        f"{doc}.injected_error_gold.json")
                if injections["status"] != "GOLD_ADJUDICATED":
                    raise ValueError("D2 injection Gold is not adjudicated")
                gold_items = gold_from_injections(injections["injections"],
                                                   geometry["segments"], doc_id)
                d2_gold.extend(gold_items)
                all_gold.extend(gold_items)
            masked = mask(source)
            clauses = segment(source, masked.masked_text, masked.pii_spans,
                              enable_plus_lists=True,
                              enable_blank_line_paragraphs=True).clauses
            segment_counts[dataset] += len(clauses)
            for clause in clauses:
                for role, label in map_dev_candidate_to_risk_labels(
                    detect_dev_risks_candidate(clause.original_text)
                ):
                    record = RiskRecord(clause.clause_id, role, label,
                                        "LEGAL_VIOLATION", clause.start_char,
                                        clause.end_char, doc_id)
                    all_predicted.append(record)
                    if dataset == "D2":
                        d2_predicted.append(record)
                    quote_total += 1
                    quote_valid += (clause.original_text == source[clause.start_char:clause.end_char])
                    for cid in _CITATIONS[label]:
                        citation_total += 1
                        provision = provisions.get(cid)
                        citation_valid += bool(
                            provision and provision.effective_from <= as_of
                            and (provision.effective_to is None or as_of <= provision.effective_to)
                        )
    if len(d2_gold) != 60 or len(all_gold) != 66:
        raise ValueError("approved Dev Gold support changed")
    return {
        "scope": "D1_D2_DEV_ARTICLE17_PLUS_SIX_D1_RISK_ITEMS",
        "classifier": "FROZEN_M5_ARTICLE17_LOCAL_RULE_PROXY_NOT_PRODUCT_M2",
        "gold_policy": "D1_M2_V02_PLUS_RATIFIED_D2_TWO_ROLE_INJECTION_V01_ON_D2_SEG_V02",
        "as_of": as_of.isoformat(),
        "source_sha256_by_document": source_hashes,
        "segment_counts": dict(segment_counts),
        "d2_dev": evaluate_risk_classification(d2_gold, d2_predicted),
        "combined_dev": evaluate_risk_classification(all_gold, all_predicted),
        "gold_tuple_counts": {"d2": len(d2_gold), "combined": len(all_gold)},
        "predicted_tuple_counts": {"d2": len(d2_predicted), "combined": len(all_predicted)},
        "m3a_local_rule_citation_proxy": {
            "status": "STATIC_ARTICLE17_MAPPING_CORPUS_EFFECTIVITY_ONLY_NOT_MODEL_CITATIONS",
            "valid": citation_valid, "total": citation_total,
            "rate": citation_valid / citation_total if citation_total else None,
        },
        "m4_exact_quote_span_local_proxy": {
            "valid": quote_valid, "total": quote_total,
            "rate": quote_valid / quote_total if quote_total else None,
        },
        "limitations": [
            "D2 two-role labels are an explicitly ratified Dev evaluation policy derived from verified injected cases.",
            "The local Article 17 detector has no UNILATERAL_CHANGE rule or independent M2 model predictions.",
            "M3a counts static law citations assigned by rule label, not citations selected by an LLM.",
            "M4 checks the local segmentation quote invariant, not a product response envelope.",
            "D1 and D2 share underlying base documents; the combined score is not independent-sample evidence.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--corpus-root", type=Path, default=Path("data/legal_corpus"))
    parser.add_argument("--as-of", type=date.fromisoformat, default=date(2026, 11, 12))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = evaluate_dev(args.data_root, args.corpus_root, as_of=args.as_of)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({"segment_counts": report["segment_counts"],
                      "gold_tuple_counts": report["gold_tuple_counts"],
                      "predicted_tuple_counts": report["predicted_tuple_counts"]}))


if __name__ == "__main__":
    main()
