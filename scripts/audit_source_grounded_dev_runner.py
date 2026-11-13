"""Run the Dev-only local provider through final_result_v1 on D1/D2.

The report contains counts and identifiers only. Source text, prompts, quotes,
private review ratings and human names are never written to the report.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from app.ai.clause_adapter import masked_items_from_segmentation
from app.ai.provider import InMemoryLedger
from app.ai.source_grounded_dev_provider import SourceGroundedDevProvider
from app.clause.dev_tfidf_baseline import DevTfidfBaseline
from app.clause.segmenter import segment
from app.core.enums import Role, SessionStatus
from app.legal.baseline_retriever import BaselineRetriever
from app.legal.corpus_loader import load_corpus
from app.privacy.masker import mask
from app.risk.dev_m2_baseline import detect_dev_m2_risks
from app.session.lock import ProcessingLease
from app.session.orchestrator import Orchestrator
from app.session.pipeline_runner import make_pipeline_runner
from app.session.store import InMemorySessionStore

_ALIAS = {"DISCIPLINE_OBLIGATION": "EMPLOYEE_OBLIGATIONS_DISCIPLINE"}


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _verified_source(path: Path, expected_sha: str) -> str:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        raise ValueError("Dev source hash differs from approved segmentation")
    return raw.decode("utf-8")


def _fit_clause_model(data_root: Path) -> DevTfidfBaseline:
    text_by_id = {}
    with (data_root / "data/processed/clauses_v06.csv").open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        for row in csv.DictReader(stream):
            if row["contract_id"] in {f"HDLD{i:03}" for i in range(1, 5)}:
                text_by_id[row["clause_id"]] = row["clause_text"]
    labels_by_id = {}
    restricted = data_root / "data/intake/restricted"
    for i in range(1, 5):
        doc = f"HDLD{i:03}"
        gold = _json(restricted / "D1_clause_label_gold_v01" /
                     f"{doc}.gold_clause_labels.json")
        labels_by_id.update({item["clause_id"]: item["labels"] for item in gold["items"]})
    if len(text_by_id) != 183 or set(text_by_id) != set(labels_by_id):
        raise ValueError("D1 Dev clause-label training inventory changed")
    ids = sorted(text_by_id)
    return DevTfidfBaseline.fit([text_by_id[key] for key in ids],
                                [labels_by_id[key] for key in ids])


def _iou(a: dict, b: dict) -> float:
    overlap = max(0, min(a["end_char"], b["end_char"])
                  - max(a["start_char"], b["start_char"]))
    union = max(a["end_char"], b["end_char"]) - min(a["start_char"], b["start_char"])
    return overlap / union if union else 0.0


def _match_review_rows(risks: list[dict], review_rows: list[dict]) -> dict:
    used = set()
    matched = []
    ambiguous = []
    exact = 0
    quote_matched = citation_matched = explanation_matched = 0
    fully_matching = 0
    mismatch_ids = {"span": [], "quote": [], "citation": [], "explanation": []}
    for row in review_rows:
        key = (row["document_id"], row["role"], row["risk_label"])
        possible = []
        for index, output in enumerate(risks):
            if index in used or (output["document_id"], output["role"],
                                 _ALIAS.get(output["risk_label"], output["risk_label"])) != key:
                continue
            score = _iou(output, row)
            if score >= 0.80:
                possible.append((score, index))
        possible.sort(reverse=True)
        if len(possible) > 1 and possible[0][0] == possible[1][0]:
            ambiguous.append(row["output_id"])
        elif possible:
            used.add(possible[0][1])
            matched.append(row["output_id"])
            output = risks[possible[0][1]]
            checks = {
                "span": (output["start_char"] == row["start_char"]
                         and output["end_char"] == row["end_char"]),
                "quote": output["masked_quote"] == row["masked_clause_text"],
                "citation": row["citation_candidate"] in output["citation_ids"],
                "explanation": output["explanation"] == row["explanation_candidate"],
            }
            exact += checks["span"]
            quote_matched += checks["quote"]
            citation_matched += checks["citation"]
            explanation_matched += checks["explanation"]
            fully_matching += all(checks.values())
            for field, passed in checks.items():
                if not passed:
                    mismatch_ids[field].append(row["output_id"])
    unmatched = [row for row in review_rows if row["output_id"] not in matched]
    diagnostics = []
    for row in unmatched:
        nearby = sorted(((_iou(output, row), output["risk_label"])
                         for output in risks
                         if output["document_id"] == row["document_id"]
                         and output["role"] == row["role"]), reverse=True)
        diagnostics.append({"output_id": row["output_id"],
                            "nearest_iou": nearby[0][0] if nearby else None,
                            "nearest_risk_label": nearby[0][1] if nearby else None})
    return {"review_rows": len(review_rows), "uniquely_matched": len(matched),
            "exact_span_matches": exact,
            "masked_quote_matches": quote_matched,
            "citation_matches": citation_matched,
            "explanation_matches": explanation_matched,
            "fully_matching_records": fully_matching,
            "mismatch_output_ids_by_field": mismatch_ids,
            "unmatched_output_ids": [row["output_id"] for row in unmatched],
            "unmatched_diagnostics": diagnostics,
            "ambiguous_output_ids": ambiguous,
            "match_rule": "document_id + role + normalized risk label + span IoU >= 0.80"}


def audit(data_root: Path, corpus_root: Path) -> dict:
    restricted = data_root / "data/intake/restricted"
    corpus = load_corpus(corpus_root)
    retriever = BaselineRetriever(corpus, final_k=8, seed_k=3)
    provisions = {row.citation_id: row for row in corpus.provisions}
    model = _fit_clause_model(data_root)
    cfg = SimpleNamespace(GEMINI_MODEL_ID="source-grounded-dev-baseline",
                          CLAUSE_BATCH_SIZE=20, RISK_BATCH_SIZE=6,
                          LLM_PARALLELISM=1, LLM_TIMEOUT_SECONDS=5,
                          LLM_AUTO_RETRY=0, CLAUSE_GRAPH_MAX_RELATED=3,
                          CLAUSE_GRAPH_MAX_CONTEXT_CHARS=6000,
                          MAX_CLAUSES=150, TEMPERATURE=0.0)
    counts = Counter()
    citation_total = citation_valid = quote_total = quote_valid = 0
    supported = insufficient = 0
    source_hashes = {}
    d2_risks = []
    d2_legacy_risks = []
    for dataset in ("D1", "D2"):
        for i in range(1, 5):
            doc = f"HDLD{i:03}"
            folder, suffix, gold_folder = (
                ("D1_m1_runtime_predictions_v01", ".canonical_nfc.txt", "D1_m1_gold_v01")
                if dataset == "D1" else
                ("D2_candidate_v02", ".d2_candidate.txt", "D2_segmentation_gold_v02")
            )
            geometry = _json(restricted / gold_folder / f"{doc}.gold_segmentation.json")
            source = _verified_source(restricted / folder / f"{doc}{suffix}",
                                      geometry["source_sha256"])
            masked_source = mask(source).masked_text
            source_hashes[f"{dataset}:{doc}"] = geometry["source_sha256"]
            if dataset == "D1":
                masking = mask(source)
                segmentation = segment(
                    source, masking.masked_text, masking.pii_spans,
                    enable_plus_lists=True, enable_blank_line_paragraphs=True)
                eligible_ids = {item.clause_id for item in
                                masked_items_from_segmentation(segmentation,
                                                               masking.masked_text)}
                for clause in segmentation.clauses:
                    text = masking.masked_text[clause.start_char:clause.end_char]
                    hits = [hit for hit in detect_dev_m2_risks(text)
                            if hit[0] == "EMPLOYEE"]
                    counts["D1_all_source_rule_tuples"] += len(hits)
                    if clause.clause_id in eligible_ids:
                        counts["D1_eligible_source_rule_tuples"] += len(hits)
                        counts["D1_eligible_multiple_rule_clauses"] += len(hits) > 1
            roles = (Role.EMPLOYEE,) if dataset == "D1" else (Role.EMPLOYEE, Role.EMPLOYER)
            runs = ((role, mode) for role in roles
                    for mode in (("v13", "packet_v11") if dataset == "D2" else ("v13",)))
            for role, mode in runs:
                store, lease = InMemorySessionStore(), ProcessingLease()
                session = store.create(role)
                if lease.try_acquire(session.session_id) != session.session_id:
                    raise RuntimeError("Dev lease unavailable")
                provider = SourceGroundedDevProvider(model)
                runner = make_pipeline_runner(source, provider, provider, {},
                                              InMemoryLedger(), cfg, corpus=corpus,
                                              retriever=retriever,
                                              enable_plus_lists=mode == "v13",
                                              enable_blank_line_paragraphs=mode == "v13")
                asyncio.run(Orchestrator(store, lease, pipeline_runner=runner).run(session))
                if session.status != SessionStatus.COMPLETED:
                    raise RuntimeError(f"Dev runner failed: {dataset}:{doc}:{role.value}")
                result = session.result
                if result["schema_version"] != "final_result_v1":
                    raise ValueError("Dev runner envelope changed")
                if mode == "packet_v11":
                    for risk in result["risks"]:
                        for label in risk["risk_labels"]:
                            d2_legacy_risks.append({
                                "document_id": doc, "role": role.value,
                                "risk_label": label, "start_char": risk["start_char"],
                                "end_char": risk["end_char"],
                                "masked_quote": masked_source[
                                    risk["start_char"]:risk["end_char"]],
                                "citation_ids": risk["citation_ids"],
                                "explanation": risk["explanation"],
                            })
                    continue
                counts[f"{dataset}_sessions"] += 1
                counts[f"{dataset}_risk_rows"] += len(result["risks"])
                for risk in result["risks"]:
                    counts[f"{dataset}_risk_label_tuples"] += len(risk["risk_labels"])
                    for label in risk["risk_labels"]:
                        counts[f"{dataset}_risk_{label}"] += 1
                    quote_total += 1
                    quote_valid += risk["quote"] == source[risk["start_char"]:risk["end_char"]]
                    supported += risk["evidence_status"] == "SUPPORTED"
                    insufficient += risk["evidence_status"] == "INSUFFICIENT_EVIDENCE"
                    for citation_id in risk["citation_ids"]:
                        citation_total += 1
                        provision = provisions.get(citation_id)
                        as_of = date.fromisoformat(session.analysis_date)
                        citation_valid += bool(
                            provision and provision.effective_from <= as_of
                            and (provision.effective_to is None or as_of <= provision.effective_to))
                    if dataset == "D2":
                        for label in risk["risk_labels"]:
                            d2_risks.append({
                                "document_id": doc, "role": role.value,
                                "risk_label": label, "start_char": risk["start_char"],
                                "end_char": risk["end_char"],
                                "masked_quote": masked_source[
                                    risk["start_char"]:risk["end_char"]],
                                "citation_ids": risk["citation_ids"],
                                "explanation": risk["explanation"],
                            })
    review_path = (restricted / "M6_D2_dev_candidate_review_v13" /
                   "D2_40_v13_ratings_minh_adjudicated.csv")
    with review_path.open(encoding="utf-8-sig", newline="") as stream:
        review_rows = list(csv.DictReader(stream))
    for row in review_rows:
        row["start_char"] = int(row["start_char"])
        row["end_char"] = int(row["end_char"])
    packet_match = _match_review_rows(d2_risks, review_rows)
    legacy_packet_match = _match_review_rows(d2_legacy_risks, review_rows)
    return {
        "status": "DEV_SOURCE_GROUNDED_LOCAL_BASELINE_NOT_PRODUCT_M2",
        "corpus_version": corpus.corpus_version,
        "graph_version": corpus.graph_version,
        "source_sha256_by_document": source_hashes,
        "counts": dict(counts),
        "m3a_candidate_effective_citations": {
            "valid": citation_valid, "total": citation_total,
            "rate": citation_valid / citation_total if citation_total else None},
        "m4_exact_quote_offset": {
            "valid": quote_valid, "total": quote_total,
            "rate": quote_valid / quote_total if quote_total else None},
        "evidence_status": {"supported": supported,
                            "insufficient_evidence": insufficient},
        "m6_prior_packet_crosswalk": packet_match,
        "m6_prior_packet_legacy_geometry_crosswalk": legacy_packet_match,
        "limitations": [
            "Local predicted clause labels and frozen source-only risk rules are Dev diagnostics.",
            "One risk_output_v2 item per clause can suppress a second rule hit on that clause.",
            "The previous M6 packet used legacy EMPLOYEE_OBLIGATIONS_DISCIPLINE; "
            "the product risk taxonomy uses DISCIPLINE_OBLIGATION.",
            "Human agreement may be attributed to this runner only for uniquely matched reviewed rows.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--corpus-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = audit(args.data_root, args.corpus_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({"counts": result["counts"],
                      "m3a": result["m3a_candidate_effective_citations"],
                      "m4": result["m4_exact_quote_offset"],
                      "m6_matched": result["m6_prior_packet_crosswalk"]["uniquely_matched"]}))


if __name__ == "__main__":
    main()
