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

from app.clause.dev_tfidf_baseline import DevTfidfBaseline
from app.legal.baseline_retriever import BaselineRetriever
from app.legal.corpus_loader import load_corpus
from app.legal.data_graph import DataGraph, get_candidates
from app.privacy.masker import mask

from ai_pipeline.evaluation.metrics.retrieval import RetrievalCase, evaluate_retrieval


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _source(path: Path, digest: str) -> str:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("Dev source hash mismatch")
    return raw.decode("utf-8")


def evaluate(data_root: Path, corpus_root: Path) -> dict:
    restricted = data_root / "data/intake/restricted"
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
    corpus = load_corpus(corpus_root)
    retriever = BaselineRetriever(corpus, final_k=8, seed_k=3)
    graph = DataGraph(corpus)
    cfg = SimpleNamespace(RETRIEVAL_FINAL_K=8, DATA_GRAPH_ENABLED=True,
                          GRAPH_MAX_NEIGHBORS_PER_SEED=4, GRAPH_MAX_CHILDREN_PER_SEED=2)
    as_of = date(2026, 11, 12)
    cases = []
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
                labels = model.predict([query])[0]
                off = retriever.retrieve(query, labels, as_of=as_of).baseline_pool
                on, did_fallback = get_candidates(retriever, graph, query, labels,
                                                   as_of, cfg)
                fallback += did_fallback
                cases.append(RetrievalCase(f"{dataset}:{doc}:{index}", citation_id,
                                           [row.citation_id for row in off],
                                           [row.citation_id for row in on],
                                           source_document_id=f"{dataset}:{doc}"))
                counts[dataset] += 1
    if counts != {"D1": 14, "D2": 60}:
        raise ValueError("Dev M8 Gold inventory changed")
    metric = evaluate_retrieval(cases, final_k=8, k=5)
    return {"status": "DEV_IN_SAMPLE_CLAUSE_LABEL_PREDICTIONS",
            "gold_counts": dict(counts), "final_k": 8, "k": 5,
            "graph_off": vars(metric.graph_off), "graph_on": vars(metric.graph_on),
            "graph_added_candidate_count": metric.graph_added_candidate_count,
            "graph_fallback_count": fallback,
            "bootstrap_cluster_count": metric.bootstrap_cluster_count,
            "limitations": [
                "D1-trained clause-label model is evaluated on D1 and D2 derivatives; this is not held-out M8.",
                "D2 two-role items share a clause query and therefore are correlated.",
            ]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--corpus-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = evaluate(args.data_root, args.corpus_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({"gold_counts": result["gold_counts"],
                      "graph_off_recall_at_5": result["graph_off"]["recall"],
                      "graph_on_recall_at_5": result["graph_on"]["recall"]}))


if __name__ == "__main__":
    main()
