"""Paired M8 diagnostic on approved D1/D2 Dev risk citations.

Uses a Dev-trained local clause label predictor. It is an in-sample Dev
diagnostic, not held-out retrieval acceptance. Writes aggregate metadata only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from app.clause.dev_tfidf_baseline import DevTfidfBaseline, add_source_working_conditions
from app.legal.baseline_retriever import BaselineRetriever
from app.legal.corpus_loader import load_corpus
from app.legal.data_graph import DataGraph, get_candidates
from app.privacy.masker import mask

from ai_pipeline.evaluation.d2_clause_gold import load_d2_gold
from ai_pipeline.evaluation.metrics.retrieval import RetrievalCase, evaluate_retrieval


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _source(path: Path, digest: str) -> str:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("Dev source hash mismatch")
    return raw.decode("utf-8")


def _source_clusters(restricted: Path) -> dict[str, str]:
    """Bind D1 and its D2 derivatives to original-source hashes, never split names."""
    original_path = restricted / "D2_candidate_v01/manifest.json"
    original = _json(original_path)
    derived = _json(restricted / "D2_candidate_v02/manifest.json")
    if (original.get("source_dataset") != "D1" or derived.get("source_d2_manifest_sha256")
            != hashlib.sha256(original_path.read_bytes()).hexdigest()):
        raise ValueError("D2 manifest lineage is not bound to the D1 source family")
    original_rows, derived_rows = original["documents"], derived["documents"]
    sources = {row["doc_id"]: row for row in original_rows}
    derivatives = {row["doc_id"]: row for row in derived_rows}
    expected = {f"HDLD{i:03}" for i in range(1, 5)}
    if len(original_rows) != 4 or len(derived_rows) != 4 or set(sources) != expected or set(derivatives) != expected:
        raise ValueError("D2 source lineage document coverage changed")
    clusters = {}
    for doc in sorted(expected):
        original_sha = hashlib.sha256((restricted / f"D1_m1_runtime_predictions_v01/{doc}.canonical_nfc.txt").read_bytes()).hexdigest()
        derived_sha = hashlib.sha256((restricted / f"D2_candidate_v02/{doc}.d2_candidate.txt").read_bytes()).hexdigest()
        if (sources[doc].get("source_d1_canonical_sha256") != original_sha
                or sources[doc].get("d2_candidate_canonical_sha256") != derived_sha
                or derivatives[doc].get("canonical_sha256") != derived_sha):
            raise ValueError(f"D1/D2 original source lineage hash mismatch: {doc}")
        clusters[doc] = original_sha
    return clusters


def evaluate(data_root: Path, corpus_root: Path, *, d2_gold_dir: Path | None = None,
             d2_review_packet: Path | None = None, allow_draft_corpus: bool = False) -> dict:
    restricted = data_root / "data/intake/restricted"
    if (d2_gold_dir is None) != (d2_review_packet is None):
        raise ValueError("D2 oracle requires both a Gold export and its signed review packet")
    d2_labels, d2_meta = (load_d2_gold(restricted, d2_gold_dir, d2_review_packet)
                          if d2_gold_dir is not None else ({}, {"input_sha256": {}}))
    source_clusters = _source_clusters(restricted)
    text_by_id = {}
    with (data_root / "data/processed/clauses_v06.csv").open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        for row in csv.DictReader(stream):
            if row["contract_id"] in {f"HDLD{i:03}" for i in range(1, 5)}:
                text_by_id[row["clause_id"]] = row["clause_text"]
    labels_by_id = {}
    for i in range(1, 5):
        doc = f"HDLD{i:03}"
        gold = _json(restricted / "D1_clause_label_gold_v01" /
                     f"{doc}.gold_clause_labels.json")
        labels_by_id.update({item["clause_id"]: item["labels"] for item in gold["items"]})
    if len(text_by_id) != 183 or set(text_by_id) != set(labels_by_id):
        raise ValueError("D1 local clause-label training inventory changed")
    keys = sorted(text_by_id)
    model = DevTfidfBaseline.fit(
        [text_by_id[key] for key in keys], [labels_by_id[key] for key in keys]
    )
    corpus = load_corpus(corpus_root, allow_draft=True) if allow_draft_corpus else load_corpus(corpus_root)
    dev_opt_in = {"allow_draft": True} if allow_draft_corpus else {}
    retriever = BaselineRetriever(corpus, final_k=8, seed_k=3, **dev_opt_in)
    graph = DataGraph(corpus, **dev_opt_in)
    cfg = SimpleNamespace(RETRIEVAL_FINAL_K=8, DATA_GRAPH_ENABLED=True,
                          GRAPH_MAX_NEIGHBORS_PER_SEED=4, GRAPH_MAX_CHILDREN_PER_SEED=2)
    as_of = date(2026, 11, 12)
    cases = []
    oracle_cases = []
    case_details = []
    counts = Counter()
    fallback = 0
    for i in range(1, 5):
        doc = f"HDLD{i:03}"
        for dataset in ("D1", "D2"):
            source_folder, source_suffix, geometry_folder = (
                ("D1_m1_runtime_predictions_v01", ".canonical_nfc.txt", "D1_m1_gold_v01")
                if dataset == "D1" else
                ("D2_candidate_v02", ".d2_candidate.txt", "D2_segmentation_gold_v02")
            )
            geometry = _json(restricted / geometry_folder / f"{doc}.gold_segmentation.json")
            source = _source(restricted / source_folder / f"{doc}{source_suffix}",
                             geometry["source_sha256"])
            spans = {item["gold_clause_ref"]: item for item in geometry["segments"]}
            if dataset == "D1":
                gold_rows = _json(restricted / "D1_m2_risk_gold_v03" /
                                  f"{doc}.risk_gold.json")["items"]
                citations = [(item["clause_id"], item["gold_citation_id"])
                             for item in gold_rows]
            else:
                injections = _json(restricted / "D2_injection_gold_v01" /
                                   f"{doc}.injected_error_gold.json")["injections"]
                citations = []
                for item in injections:
                    if not item["verification"] or any(
                        review["decision"] != "VERIFIED" for review in item["verification"]
                    ):
                        raise ValueError("D2 injection is not verified")
                    citations.extend([(item["clause_id"],
                                       item["gold_citation_id"])] * 2)
            masked = mask(source).masked_text
            for index, (clause_id, citation_id) in enumerate(citations):
                span = spans[clause_id]
                query = masked[span["start_char"]:span["end_char"]]
                labels = add_source_working_conditions([query], model.predict([query]))[0]
                retrieved = retriever.retrieve(query, labels, as_of=as_of)
                off = retrieved.baseline_pool
                on, did_fallback = get_candidates(retriever, graph, query, labels,
                                                   as_of, cfg)
                fallback += did_fallback
                case_id = f"{dataset}:{doc}:{index}"
                off_ids = [row.citation_id for row in off]
                on_ids = [row.citation_id for row in on]
                cases.append(RetrievalCase(case_id, citation_id, off_ids, on_ids,
                                           source_document_id=source_clusters[doc]))
                detail = {
                    "case_id": case_id, "gold_clause_ref": clause_id,
                    "gold_citation_id": citation_id, "predicted_clause_labels": labels,
                    "primary_off_rank": off_ids.index(citation_id) + 1
                    if citation_id in off_ids else None,
                    "primary_on_rank": on_ids.index(citation_id) + 1
                    if citation_id in on_ids else None,
                    "gold_label_weight": max(
                        (corpus.label_map.get(label, {}).get(citation_id, 0.0)
                         for label in labels), default=0.0),
                    "gold_reachable_from_graph_seeds": any(
                        neighbor.citation_id == citation_id
                        for seed in retrieved.seeds
                        for neighbor in graph.neighbors(seed.citation_id, as_of=as_of)),
                    "graph_seed_citation_ids": [row.citation_id for row in retrieved.seeds],
                }
                if dataset == "D1" or d2_labels:
                    oracle_labels = labels_by_id[clause_id] if dataset == "D1" else d2_labels[doc][clause_id]
                    oracle_off = [row.citation_id for row in
                                  retriever.retrieve(query, oracle_labels,
                                                     as_of=as_of).baseline_pool]
                    oracle_on_rows, _ = get_candidates(
                        retriever, graph, query, oracle_labels, as_of, cfg)
                    oracle_on = [row.citation_id for row in oracle_on_rows]
                    oracle_cases.append(RetrievalCase(
                        case_id, citation_id, oracle_off, oracle_on,
                        source_document_id=source_clusters[doc]))
                    detail["oracle_clause_labels"] = oracle_labels
                    detail["oracle_off_rank"] = (oracle_off.index(citation_id) + 1
                                                  if citation_id in oracle_off else None)
                    detail["oracle_on_rank"] = (oracle_on.index(citation_id) + 1
                                                 if citation_id in oracle_on else None)
                case_details.append(detail)
                counts[dataset] += 1
    if counts != {"D1": 14, "D2": 60}:
        raise ValueError("Dev M8 Gold inventory changed")
    metric = evaluate_retrieval(cases, final_k=8, k=5)
    oracle_metric = evaluate_retrieval(oracle_cases, final_k=8, k=5)
    def by_dataset(rows):
        result = {}
        for dataset in ("D1", "D2"):
            subset = [row for row in rows if row.case_id.startswith(dataset + ":")]
            if subset:
                score = evaluate_retrieval(subset, final_k=8, k=5)
                result[dataset] = {"total": len(subset), "graph_off": vars(score.graph_off),
                                   "graph_on": vars(score.graph_on)}
        return result
    primary_by_dataset, oracle_by_dataset = by_dataset(cases), by_dataset(oracle_cases)
    missed = [item for item in case_details
              if item["primary_off_rank"] is None or item["primary_off_rank"] > 5]
    gained = [item["case_id"] for item in case_details
              if (item["primary_off_rank"] is None or item["primary_off_rank"] > 5)
              and item["primary_on_rank"] is not None and item["primary_on_rank"] <= 5]
    lost = [item["case_id"] for item in case_details
            if item["primary_off_rank"] is not None and item["primary_off_rank"] <= 5
            and (item["primary_on_rank"] is None or item["primary_on_rank"] > 5)]
    inputs = [data_root / "data/processed/clauses_v06.csv"]
    inputs.extend(restricted / name for name in ("D2_candidate_v01/manifest.json", "D2_candidate_v02/manifest.json"))
    for i in range(1, 5):
        doc = f"HDLD{i:03}"
        inputs.extend(restricted / item for item in (
            f"D1_clause_label_gold_v01/{doc}.gold_clause_labels.json",
            f"D1_m1_runtime_predictions_v01/{doc}.canonical_nfc.txt",
            f"D1_m1_gold_v01/{doc}.gold_segmentation.json",
            f"D1_m2_risk_gold_v03/{doc}.risk_gold.json",
            f"D2_candidate_v02/{doc}.d2_candidate.txt",
            f"D2_segmentation_gold_v02/{doc}.gold_segmentation.json",
            f"D2_injection_gold_v01/{doc}.injected_error_gold.json",
        ))
    return {"status": "DEV_IN_SAMPLE_CLAUSE_LABEL_PREDICTIONS",
            "protocol_version": ("m8_dev_2026-11-24_v3_owner_d2_gold" if d2_labels
                                 else "m8_dev_paired_rc01_2026-11-23_v2_original_source_clusters"),
            "bootstrap_cluster_policy": "ORIGINAL_D1_SOURCE_SHA256_V1",
            "original_source_clusters": source_clusters,
            "analysis_date": as_of.isoformat(),
            "input_sha256": {**{p.relative_to(data_root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
                             **{"d2_clause_gold/"+key: value for key, value in d2_meta["input_sha256"].items()}},
            "d2_gold_version": d2_meta.get("dataset_version"),
            "predictor_sha256": hashlib.sha256(
                (Path(__file__).resolve().parents[1] / "backend/app/clause/dev_tfidf_baseline.py").read_bytes()).hexdigest(),
            "held_out_used": False,
            "corpus_version": corpus.corpus_version,
            "graph_version": corpus.graph_version,
            "corpus_release_status": corpus.release_status,
            "draft_dev_opt_in": allow_draft_corpus,
            "gold_counts": dict(counts), "final_k": 8, "k": 5,
            "seed_k": 3,
            "graph_off": vars(metric.graph_off), "graph_on": vars(metric.graph_on),
            "graph_added_candidate_count": metric.graph_added_candidate_count,
            "graph_fallback_count": fallback,
            "bootstrap_cluster_count": metric.bootstrap_cluster_count,
            "m8_primary": {"graph_off": vars(metric.graph_off),
                           "graph_on": vars(metric.graph_on), "total": len(cases)},
            "m8_primary_by_dataset": primary_by_dataset,
            "m8_oracle_by_dataset": oracle_by_dataset,
            "m8_oracle_labels": {"scope": "D1_PLUS_D2_ADJUDICATED_CLAUSE_GOLD" if d2_labels else "D1_ONLY_ADJUDICATED_CLAUSE_GOLD",
                                 "graph_off": vars(oracle_metric.graph_off),
                                 "graph_on": vars(oracle_metric.graph_on),
                                 "total": len(oracle_cases)},
            "m8_oracle_d1_plus_d2_clauses_v07": ({
                "status": "AVAILABLE", "gold_version": d2_meta.get("dataset_version"),
                "total": len(oracle_cases), "graph_off": vars(oracle_metric.graph_off),
                "graph_on": vars(oracle_metric.graph_on),
            } if d2_labels else {
                "status": "UNAVAILABLE",
                "reason": "D2_v02/clauses_v07.csv adjudicated source is absent; "
                          "a pending mixed-source v07 file is not D2 Gold.",
            }),
            "primary_missed_cases": missed,
            "dev_case_details": case_details,
            "primary_graph_gained_case_ids": gained,
            "primary_graph_lost_case_ids": lost,
            "oracle_label_coverage": {key: value["total"] for key, value in oracle_by_dataset.items()}
            if d2_labels else {"D1": len(oracle_cases), "D2": 0},
            "limitations": [
                "D1-trained clause-label model is evaluated on D1 and D2 derivatives; this is not held-out M8.",
                "D2 two-role items share a clause query and therefore are correlated.",
                "D1 and D2 derivatives share original-document bootstrap clusters; four source families are insufficient for generalization claims.",
                ("D2 Owner-adjudicated labels are used for oracle only, not to retrain or tune the primary model."
                 if d2_labels else "D2 has no adjudicated clause-label Gold; a74-case oracle estimate is unavailable."),
            ]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--corpus-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--d2-gold-dir", type=Path)
    parser.add_argument("--d2-review-packet", type=Path)
    parser.add_argument("--allow-draft-corpus", action="store_true", help="explicit Dev-only opt-in, never runtime approval")
    args = parser.parse_args()
    result = evaluate(args.data_root, args.corpus_root, d2_gold_dir=args.d2_gold_dir,
                      d2_review_packet=args.d2_review_packet, allow_draft_corpus=args.allow_draft_corpus)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({"gold_counts": result["gold_counts"],
                      "graph_off_recall_at_5": result["graph_off"]["recall"],
                      "graph_on_recall_at_5": result["graph_on"]["recall"]}))


if __name__ == "__main__":
    main()
