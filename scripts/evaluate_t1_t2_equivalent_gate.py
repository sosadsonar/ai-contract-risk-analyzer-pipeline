"""Score independent local segmentation on the three equivalent-gate slices and T2.

Prediction happens before Gold is opened. Raw text and predicted offsets stay in
the restricted Data repository; the public report contains counts and hashes.
"""

import argparse
import csv
import hashlib
import itertools
import json
from collections import Counter
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from app.clause.dev_tfidf_baseline import DevTfidfBaseline
from app.clause.segmenter import SEGMENTATION_VERSION, segment
from app.legal.baseline_retriever import BaselineRetriever
from app.legal.corpus_loader import load_corpus
from app.legal.data_graph import DataGraph, get_candidates
from app.privacy.detector import detect
from app.privacy.masker import mask
from app.risk.dev_injection_baseline import detect_dev_risks

from ai_pipeline.evaluation.metrics.bootstrap import bootstrap_cluster_interval
from ai_pipeline.evaluation.metrics.citation_validity import (
    CitationCheck,
    evaluate_citation_validity,
)
from ai_pipeline.evaluation.metrics.clause_classification_cases import (
    ClauseClassificationCase,
    evaluate_clause_classification,
)
from ai_pipeline.evaluation.metrics.injected_recall import (
    InjectedErrorCase,
    RiskPrediction,
    evaluate_injected_recall,
)
from ai_pipeline.evaluation.metrics.privacy import PreserveSpan, PrivacySpan, evaluate_privacy
from ai_pipeline.evaluation.metrics.quote_span import QuoteSpanCase, evaluate_quote_spans
from ai_pipeline.evaluation.metrics.retrieval import RetrievalCase, evaluate_retrieval
from ai_pipeline.evaluation.metrics.segmentation import CharacterSpan, evaluate_segmentation

SLICES = {
    "slice_unique_8": [f"HDLD{i:03}" for i in (5, 7, 8, 9, 10, 11, 12, 13)],
    "slice_t1_real_9": [f"HDLD{i:03}" for i in range(5, 14)],
    "slice_composite_10": [f"HDLD{i:03}" for i in range(5, 15)],
    "T2": [f"HDLD{i:03}" for i in range(5, 14)],
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def f1(rows):
    tp, fp, fn = (sum(row[key] for row in rows) for key in ("tp", "fp", "fn"))
    return 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None


def macro_f1_sampled(rows):
    gold, predicted, tp = Counter(), Counter(), Counter()
    for row in rows:
        actual, estimate = set(row.gold_labels), set(row.predicted_labels)
        gold.update(actual)
        predicted.update(estimate)
        tp.update(actual & estimate)
    supported = [label for label, count in gold.items() if count >= 5]
    if not supported:
        return None
    return sum(
        2 * tp[label] / (gold[label] + predicted[label]) if gold[label] + predicted[label] else 0.0
        for label in supported
    ) / len(supported)


def derive_inserted_privacy_spans(source, injected, injections, pii_rows, preserve_rows):
    """Project adjudicated T1 privacy offsets across verified T2 insertions.

    Only newline envelopes that reconstruct the exact T1 NFC text are allowed.
    Every mapped span must remain in one untouched chunk and quote identically.
    Ambiguous mapped offsets fail closed.
    """
    spans = sorted((item["insertion_span"]["start_char"], item["insertion_span"]["end_char"]) for item in injections)
    if any(detect(injected[start:end]) for start, end in spans):
        raise ValueError("T2 insertion contains new PII detector hits; derivation requires review")
    mapped_solutions = set()
    for before_counts in itertools.product((0, 1, 2), repeat=len(spans)):
        envelopes = [
            (start - before, end + 2 - before) for (start, end), before in zip(spans, before_counts, strict=True)
        ]
        if any(
            left < 0 or right > len(injected) or injected[left:start] + injected[end:right] != "\n\n"
            for (start, end), (left, right) in zip(spans, envelopes, strict=True)
        ):
            continue
        if any(envelopes[index][1] > envelopes[index + 1][0] for index in range(len(envelopes) - 1)):
            continue
        chunks = []
        source_offset = 0
        previous_end = 0
        for left, right in [*envelopes, (len(injected), len(injected))]:
            chunk = injected[previous_end:left]
            chunks.append((source_offset, source_offset + len(chunk), previous_end))
            source_offset += len(chunk)
            previous_end = right
        if "".join(injected[t2_start : t2_start + end - start] for start, end, t2_start in chunks) != source:
            continue

        def project(rows):
            projected = []
            for row in rows:
                start, end = row["start_char"], row["end_char"]
                owner = next(
                    (
                        (base_start, t2_start)
                        for base_start, base_end, t2_start in chunks
                        if base_start <= start < end <= base_end
                    ),
                    None,
                )
                if owner is None:
                    return None
                base_start, t2_start = owner
                mapped_start = t2_start + start - base_start
                mapped_end = t2_start + end - base_start
                if source[start:end] != injected[mapped_start:mapped_end]:
                    return None
                projected.append((mapped_start, mapped_end))
            return tuple(projected)

        pii = project(pii_rows)
        preserve = project(preserve_rows)
        if pii is not None and preserve is not None:
            mapped_solutions.add((pii, preserve))
    if len(mapped_solutions) != 1:
        raise ValueError("T2 privacy offset projection is missing or ambiguous")
    return mapped_solutions.pop()


def evaluate(data_root):
    restricted = data_root / "data/intake/restricted"
    source_paths = {
        **{
            ("T1", f"HDLD{i:03}"): restricted / "T1_segmentation_candidate_v01" / f"HDLD{i:03}.txt"
            for i in range(5, 14)
        },
        ("T1", "HDLD014"): data_root / "data/processed/raw_text/HDLD014.txt",
        **{
            ("T2", f"HDLD{i:03}"): restricted / "T2_candidate_v02" / f"HDLD{i:03}_T2_candidate.txt"
            for i in range(5, 14)
        },
    }
    predicted = {}
    privacy_predictions = {}
    t2_privacy_predictions = {}
    quote_predictions = {}
    for key, path in source_paths.items():
        text = path.read_text(encoding="utf-8")
        masked = mask(text)
        result = segment(text, masked.masked_text, masked.pii_spans)
        predicted[key] = {
            "source_sha256": digest(path),
            "spans": [[row.start_char, row.end_char] for row in result.clauses],
        }
        detected = [(row, role, label) for row in result.clauses for role, label in detect_dev_risks(row.original_text)]
        predicted[key]["risk_candidates"] = [
            {"start_char": row.start_char, "end_char": row.end_char, "role": role, "risk_label": label}
            for row, role, label in detected
        ]
        quote_predictions[key] = [
            QuoteSpanCase(text, row.original_text, row.start_char, row.end_char, key[1]) for row, _, _ in detected
        ]
        if key[0] == "T1":
            privacy_predictions[key[1]] = (text, masked)
        else:
            t2_privacy_predictions[key[1]] = (text, masked)

    # Train only on four Dev documents. Candidate T1 boundaries supply input
    # coordinates; candidate labels and all T1 Gold labels remain unread.
    d1_source = data_root / "data/processed/clauses_v06.csv"
    with d1_source.open(encoding="utf-8-sig", newline="") as stream:
        d1_text = {
            row["clause_id"]: row["clause_text"]
            for row in csv.DictReader(stream)
            if row["contract_id"] in {f"HDLD{i:03}" for i in range(1, 5)}
        }
    d1_gold_root = restricted / "D1_clause_label_gold_v01"
    d1_labels = {}
    for index in range(1, 5):
        doc = f"HDLD{index:03}"
        gold = json.loads((d1_gold_root / f"{doc}.gold_clause_labels.json").read_text(encoding="utf-8"))
        d1_labels.update({row["clause_id"]: row["labels"] for row in gold["items"]})
    if len(d1_text) != 183 or set(d1_text) != set(d1_labels):
        raise ValueError("D1 Dev training corpus must have 183 matched clauses")
    train_ids = sorted(d1_text)
    model = DevTfidfBaseline.fit(
        [d1_text[clause_id] for clause_id in train_ids], [d1_labels[clause_id] for clause_id in train_ids]
    )
    query_keys, query_texts, query_spans = [], [], []
    for doc in SLICES["slice_composite_10"]:
        text = privacy_predictions[doc][0]
        if doc == "HDLD014":
            candidate = json.loads(
                (data_root / "data/intake/private/HDLD014_synthetic_candidate_v01.json").read_text(encoding="utf-8")
            )
            rows = [
                (row["clause_id"], row["start_char"], row["end_char"]) for row in candidate["segmentation_candidates"]
            ]
        else:
            candidate = json.loads(
                (restricted / "T1_segmentation_candidate_v01" / f"{doc}_segments.json").read_text(encoding="utf-8")
            )
            if candidate["canonical_text_sha256"] != predicted[("T1", doc)]["source_sha256"]:
                raise ValueError(f"T1 input boundary source hash mismatch for {doc}")
            rows = [
                (row["candidate_segment_id"], row["start_char"], row["end_char"])
                for row in candidate["segments"]
                if row["kind"] == "CLAUSE"
            ]
        for clause_id, start, end in rows:
            if not 0 <= start < end <= len(text):
                raise ValueError(f"invalid M7 input span for {doc}")
            query_keys.append((doc, clause_id))
            query_texts.append(text[start:end])
            query_spans.append((start, end))
    if len(query_keys) != 757 or len(set(query_keys)) != 757:
        raise ValueError("M7 must predict 747 T1 spans plus 10 synthetic control spans")
    m7_predictions = {doc: {} for doc in SLICES["slice_composite_10"]}
    for (doc, clause_id), labels in zip(query_keys, model.predict(query_texts), strict=True):
        m7_predictions[doc][clause_id] = labels
    for doc, clauses in m7_predictions.items():
        predicted[("T1", doc)]["clause_label_predictions"] = [
            {"clause_id": clause_id, "predicted_labels": labels} for clause_id, labels in sorted(clauses.items())
        ]
    # The genuine-clause slice has 340 resegmented reference spans, including
    # new IDs absent from the 747-row full manifest. Read only IDs/coordinates
    # here. Their Gold label values are accessed later, after inference.
    clean_path = data_root / "data/processed/clauses_v08.csv"
    with clean_path.open(encoding="utf-8-sig", newline="") as stream:
        clean_boundaries = [
            (row["contract_id"], row["clause_id"], int(row["start_offset"]), int(row["end_offset"]))
            for row in csv.DictReader(stream)
            if row["contract_id"] in SLICES["slice_t1_real_9"]
        ]
    if len(clean_boundaries) != 340 or len({(doc, clause_id) for doc, clause_id, _, _ in clean_boundaries}) != 340:
        raise ValueError("genuine T1 slice must have 340 unique reference spans")
    clean_source_text = {
        doc: (data_root / "data/processed/raw_text" / f"{doc}.txt").read_text(encoding="utf-8")
        for doc in SLICES["slice_t1_real_9"]
    }
    clean_queries = []
    for doc, _, start, end in clean_boundaries:
        text = clean_source_text[doc]
        if not 0 <= start < end <= len(text):
            raise ValueError(f"invalid genuine M7 input span for {doc}")
        clean_queries.append(text[start:end])
    m7_clean_predictions = {doc: {} for doc in SLICES["slice_t1_real_9"]}
    for (doc, clause_id, _, _), labels in zip(clean_boundaries, model.predict(clean_queries), strict=True):
        m7_clean_predictions[doc][clause_id] = labels
    for doc, clauses in m7_clean_predictions.items():
        predicted[("T1", doc)]["genuine_clause_label_predictions"] = [
            {"clause_id": clause_id, "predicted_labels": labels} for clause_id, labels in sorted(clauses.items())
        ]

    corpus_path = Path(__file__).resolve().parents[1] / "data/legal_corpus"
    corpus = load_corpus(corpus_path)
    retriever = BaselineRetriever(corpus, final_k=8, seed_k=3)
    graph = DataGraph(corpus)
    config = SimpleNamespace(
        RETRIEVAL_FINAL_K=8, DATA_GRAPH_ENABLED=True, GRAPH_MAX_NEIGHBORS_PER_SEED=4, GRAPH_MAX_CHILDREN_PER_SEED=2
    )
    analysis_date = date(2026, 11, 5)
    for (doc, clause_id), (start, end) in zip(query_keys, query_spans, strict=True):
        masked_text = privacy_predictions[doc][1].masked_text[start:end]
        labels = m7_predictions[doc][clause_id]
        candidates = retriever.retrieve(masked_text, labels, as_of=analysis_date).baseline_pool
        predicted[("T1", doc)].setdefault("citation_predictions", []).append(
            {
                "clause_id": clause_id,
                "citation_id": candidates[0].citation_id if candidates else None,
                "retrieval_trace": [row.citation_id for row in candidates],
            }
        )
    for doc in SLICES["T2"]:
        source = source_paths[("T2", doc)].read_text(encoding="utf-8")
        masked = mask(source)
        spans = predicted[("T2", doc)]["spans"]
        labels_by_span = model.predict([masked.masked_text[start:end] for start, end in spans])
        retrieval_rows = []
        for (start, end), labels in zip(spans, labels_by_span, strict=True):
            query = masked.masked_text[start:end]
            off = retriever.retrieve(query, labels, as_of=analysis_date).baseline_pool
            on, fallback = get_candidates(retriever, graph, query, labels, analysis_date, config)
            retrieval_rows.append(
                {
                    "start_char": start,
                    "end_char": end,
                    "predicted_labels": labels,
                    "baseline_candidate_ids": [row.citation_id for row in off],
                    "graph_candidate_ids": [row.citation_id for row in on],
                    "graph_fallback": fallback,
                }
            )
        predicted[("T2", doc)]["retrieval_predictions"] = retrieval_rows

    counts = {}
    for (dataset, doc), prediction in predicted.items():
        folder = (
            restricted / "HDLD014_synthetic_control_gold_v01"
            if doc == "HDLD014"
            else restricted / f"{dataset}_segmentation_gold_v01"
        )
        gold = json.loads((folder / f"{doc}.gold_segmentation.json").read_text(encoding="utf-8"))
        if gold["source_sha256"] != prediction["source_sha256"]:
            raise ValueError(f"source hash mismatch for {dataset}/{doc}")
        result = evaluate_segmentation(
            [CharacterSpan(row["start_char"], row["end_char"]) for row in gold["segments"]],
            [CharacterSpan(start, end) for start, end in prediction["spans"]],
        )
        counts[(dataset, doc)] = {
            key: getattr(result, key) for key in ("gold_count", "predicted_count", "tp", "fp", "fn")
        }

    metrics = {}
    privacy_counts = {}
    for doc, (text, masked) in privacy_predictions.items():
        folder = (
            restricted / "HDLD014_synthetic_control_gold_v01"
            if doc == "HDLD014"
            else restricted / "T1_privacy_gold_v01"
        )
        gold = json.loads((folder / f"{doc}.gold_privacy.json").read_text(encoding="utf-8"))
        result = evaluate_privacy(
            text,
            masked.masked_text,
            predicted_spans=[PrivacySpan(row.type.value, row.start, row.end) for row in masked.pii_spans],
            gold_pii_spans=[
                PrivacySpan(row["pii_type"], row["start_char"], row["end_char"]) for row in gold["pii_spans"]
            ],
            preserve_spans=[PreserveSpan(row["start_char"], row["end_char"]) for row in gold["preserve_spans"]],
        )
        privacy_counts[doc] = {
            "high_gold": result.high_sensitivity.gold_count,
            "high_masked": result.high_sensitivity.masked_count,
            "standard_gold": result.standard_sensitivity.gold_count,
            "standard_masked": result.standard_sensitivity.masked_count,
            "preserve_gold": result.preserve_count,
            "preserved": result.preserved_count,
        }
    for name, docs in SLICES.items():
        dataset = "T2" if name == "T2" else "T1"
        selected = {doc: counts[(dataset, doc)] for doc in docs}
        interval = bootstrap_cluster_interval(
            {doc: [row] for doc, row in selected.items()},
            f1,
            iterations=1000,
            random_seed=0,
        )
        metrics[name] = {
            "M1": {
                "status": "TECHNICAL_SCORE",
                "score": f1(selected.values()),
                "gold_spans": sum(row["gold_count"] for row in selected.values()),
                "predicted_spans": sum(row["predicted_count"] for row in selected.values()),
                "ci95": {
                    "low": interval.low,
                    "high": interval.high,
                    "iterations": 1000,
                    "seed": 0,
                    "cluster_count": interval.cluster_count,
                    "valid_replicates": interval.valid_replicate_count,
                },
            }
        }
        if dataset == "T1":
            p_rows = {doc: privacy_counts[doc] for doc in docs}
            metrics[name]["PRIVACY"] = {
                "status": "TECHNICAL_SCORE",
                "counts": {key: sum(row[key] for row in p_rows.values()) for key in next(iter(p_rows.values()))},
            }
            for group, numerator, denominator in (
                ("high_sensitivity_recall", "high_masked", "high_gold"),
                ("standard_sensitivity_recall", "standard_masked", "standard_gold"),
                ("preserve_rate", "preserved", "preserve_gold"),
            ):

                def rate(rows):
                    total = sum(row[denominator] for row in rows)
                    return sum(row[numerator] for row in rows) / total if total else None

                ci = bootstrap_cluster_interval(
                    {doc: [row] for doc, row in p_rows.items()}, rate, iterations=1000, random_seed=0
                )
                metrics[name]["PRIVACY"][group] = {
                    "score": rate(p_rows.values()),
                    "ci95": {
                        "low": ci.low,
                        "high": ci.high,
                        "iterations": 1000,
                        "seed": 0,
                        "valid_replicates": ci.valid_replicate_count,
                    },
                }
    injected_gold = []
    aligned_predictions = []
    for doc in SLICES["T2"]:
        injection_file = restricted / "T2_injection_gold_v01" / f"{doc}.injected_error_gold.json"
        injection_rows = json.loads(injection_file.read_text(encoding="utf-8"))["injections"]
        for item in injection_rows:
            injected_gold.append(
                InjectedErrorCase(
                    item["injection_id"],
                    item["clause_id"],
                    item["role"],
                    item["risk_label"],
                    doc,
                )
            )
            target = item["insertion_span"]
            start, end = target["start_char"], target["end_char"]
            for risk in predicted[("T2", doc)]["risk_candidates"]:
                overlap = max(0, min(end, risk["end_char"]) - max(start, risk["start_char"]))
                if overlap / (end - start) >= 0.8:
                    aligned_predictions.append(
                        RiskPrediction(
                            item["clause_id"],
                            risk["role"],
                            risk["risk_label"],
                            doc,
                        )
                    )
    m5 = evaluate_injected_recall(injected_gold, aligned_predictions)
    if m5.total != 30:
        raise ValueError("T2 must have exactly 30 adjudicated injections")
    metrics["T2"]["M5"] = {
        "status": "TECHNICAL_SCORE",
        "score": m5.recall,
        "hits": m5.hits,
        "total": m5.total,
        "ci95": {
            "low": m5.recall_ci95_low,
            "high": m5.recall_ci95_high,
            "iterations": m5.bootstrap_iterations,
            "seed": 0,
            "cluster_count": m5.bootstrap_cluster_count,
            "valid_replicates": m5.bootstrap_valid_replicate_count,
        },
        "prediction_module": "app.risk.dev_injection_baseline.detect_dev_risks",
        "alignment_rule": "Predicted segment covers at least 80% of injection span; role and risk label match.",
        "limitation": "This is the frozen Dev Article 17 OR rule, not the full W7 composite 27/30 predictor.",
    }
    derived_privacy = {}
    t2_privacy_counts = {}
    for doc in SLICES["T2"]:
        source = source_paths[("T1", doc)].read_text(encoding="utf-8")
        text, masked = t2_privacy_predictions[doc]
        t1_file = restricted / "T1_privacy_gold_v01" / f"{doc}.gold_privacy.json"
        t2_file = restricted / "T2_injection_gold_v01" / f"{doc}.injected_error_gold.json"
        t1_gold = json.loads(t1_file.read_text(encoding="utf-8"))
        injections = json.loads(t2_file.read_text(encoding="utf-8"))["injections"]
        pii_offsets, preserve_offsets = derive_inserted_privacy_spans(
            source,
            text,
            injections,
            t1_gold["pii_spans"],
            t1_gold["preserve_spans"],
        )
        derived_privacy[doc] = {
            "source_sha256": digest(source_paths[("T1", doc)]),
            "injected_sha256": digest(source_paths[("T2", doc)]),
            "t1_privacy_gold_sha256": digest(t1_file),
            "t2_injection_gold_sha256": digest(t2_file),
            "pii_spans": [
                {"start_char": start, "end_char": end, "pii_type": row["pii_type"]}
                for row, (start, end) in zip(t1_gold["pii_spans"], pii_offsets, strict=True)
            ],
            "preserve_spans": [
                {"start_char": start, "end_char": end, "field": row["field"]}
                for row, (start, end) in zip(t1_gold["preserve_spans"], preserve_offsets, strict=True)
            ],
        }
        result = evaluate_privacy(
            text,
            masked.masked_text,
            predicted_spans=[PrivacySpan(row.type.value, row.start, row.end) for row in masked.pii_spans],
            gold_pii_spans=[
                PrivacySpan(row["pii_type"], start, end)
                for row, (start, end) in zip(t1_gold["pii_spans"], pii_offsets, strict=True)
            ],
            preserve_spans=[PreserveSpan(start, end) for start, end in preserve_offsets],
        )
        t2_privacy_counts[doc] = {
            "high_gold": result.high_sensitivity.gold_count,
            "high_masked": result.high_sensitivity.masked_count,
            "standard_gold": result.standard_sensitivity.gold_count,
            "standard_masked": result.standard_sensitivity.masked_count,
            "preserve_gold": result.preserve_count,
            "preserved": result.preserved_count,
        }
    metrics["T2"]["PRIVACY"] = {
        "status": "TECHNICAL_SCORE_DERIVED_REFERENCE",
        "counts": {
            key: sum(row[key] for row in t2_privacy_counts.values()) for key in next(iter(t2_privacy_counts.values()))
        },
        "reference_status": "DERIVED_FROM_T1_ADJUDICATED_AND_T2_INJECTIONS_NOT_SEPARATELY_ADJUDICATED",
    }
    for group, numerator, denominator in (
        ("high_sensitivity_recall", "high_masked", "high_gold"),
        ("standard_sensitivity_recall", "standard_masked", "standard_gold"),
        ("preserve_rate", "preserved", "preserve_gold"),
    ):

        def rate(rows):
            total = sum(row[denominator] for row in rows)
            return sum(row[numerator] for row in rows) / total if total else None

        interval = bootstrap_cluster_interval(
            {doc: [row] for doc, row in t2_privacy_counts.items()},
            rate,
            iterations=1000,
            random_seed=0,
        )
        metrics["T2"]["PRIVACY"][group] = {
            "score": rate(t2_privacy_counts.values()),
            "ci95": {
                "low": interval.low,
                "high": interval.high,
                "iterations": 1000,
                "seed": 0,
                "valid_replicates": interval.valid_replicate_count,
            },
        }
    retrieval_cases = []
    unlocalized = []
    for doc in SLICES["T2"]:
        injection_file = restricted / "T2_injection_gold_v01" / f"{doc}.injected_error_gold.json"
        for item in json.loads(injection_file.read_text(encoding="utf-8"))["injections"]:
            target = item["insertion_span"]
            start, end = target["start_char"], target["end_char"]
            ranked = sorted(
                predicted[("T2", doc)]["retrieval_predictions"],
                key=lambda row: (-max(0, min(end, row["end_char"]) - max(start, row["start_char"])), row["start_char"]),
            )
            best = ranked[0] if ranked else None
            coverage = (
                max(0, min(end, best["end_char"]) - max(start, best["start_char"])) / (end - start) if best else 0.0
            )
            if coverage < 0.8:
                unlocalized.append(item["injection_id"])
            retrieval_cases.append(
                RetrievalCase(
                    item["injection_id"],
                    item["gold_citation_id"],
                    best["baseline_candidate_ids"] if coverage >= 0.8 else (),
                    best["graph_candidate_ids"] if coverage >= 0.8 else (),
                    doc,
                )
            )
    m8 = evaluate_retrieval(retrieval_cases, final_k=8, k=5)
    metrics["T2"]["M8"] = {
        "status": "TECHNICAL_SCORE",
        "total": m8.graph_on.total,
        "graph_off": {
            "hits": m8.graph_off.hits,
            "score": m8.graph_off.recall,
            "ci95": [m8.graph_off.ci95_low, m8.graph_off.ci95_high],
        },
        "graph_on": {
            "hits": m8.graph_on.hits,
            "score": m8.graph_on.recall,
            "ci95": [m8.graph_on.ci95_low, m8.graph_on.ci95_high],
        },
        "bootstrap": {"iterations": m8.bootstrap_iterations, "seed": 0, "cluster_count": m8.bootstrap_cluster_count},
        "unlocalized_injection_count": len(unlocalized),
        "final_k": 8,
        "k": 5,
        "prediction_modules": [
            "app.clause.dev_tfidf_baseline.DevTfidfBaseline",
            "app.legal.baseline_retriever.BaselineRetriever",
            "app.legal.data_graph.get_candidates",
        ],
    }
    for slice_name, docs in SLICES.items():
        dataset = "T2" if slice_name == "T2" else "T1"
        quote_cases = [case for doc in docs for case in quote_predictions[(dataset, doc)]]
        quote_result = evaluate_quote_spans(quote_cases)
        metrics[slice_name]["M4"] = {
            "status": "TECHNICAL_SCORE" if quote_result.total else "NO_EMITTED_RISK_OUTPUTS",
            "valid": quote_result.valid,
            "total": quote_result.total,
            "score": quote_result.rate,
            "ci95": {
                "low": quote_result.rate_ci95_low,
                "high": quote_result.rate_ci95_high,
                "iterations": quote_result.bootstrap_iterations,
                "seed": 0,
                "cluster_count": quote_result.bootstrap_cluster_count,
                "valid_replicates": quote_result.bootstrap_valid_replicate_count,
            },
            "limitation": (
                "Exact quote/offset invariant on emitted Dev-rule risk candidates only; "
                "it does not measure missed risks."
            ),
        }
        checks = []
        for doc in docs:
            dataset = "T2" if slice_name == "T2" else "T1"
            if dataset == "T2":
                traces = predicted[("T2", doc)]["retrieval_predictions"]
                checks.extend(
                    CitationCheck(
                        row["baseline_candidate_ids"][0], tuple(row["baseline_candidate_ids"]), analysis_date, doc
                    )
                    for row in traces
                    if row["baseline_candidate_ids"]
                )
            else:
                traces = predicted[("T1", doc)]["citation_predictions"]
                checks.extend(
                    CitationCheck(row["citation_id"], tuple(row["retrieval_trace"]), analysis_date, doc)
                    for row in traces
                    if row["citation_id"]
                )
        result = evaluate_citation_validity(checks, corpus, as_of=analysis_date)
        metrics[slice_name]["M3a"] = {
            "status": "TECHNICAL_SCORE",
            "total": result.total,
            "valid": result.valid,
            "score": result.rate,
            "ci95": {
                "low": result.rate_ci95_low,
                "high": result.rate_ci95_high,
                "iterations": result.bootstrap_iterations,
                "seed": 0,
                "cluster_count": result.bootstrap_cluster_count,
                "valid_replicates": result.bootstrap_valid_replicate_count,
            },
            "limitation": (
                "Citation membership/effectivity for emitted top-1 retrieval candidates; "
                "not citation relevance or risk accuracy."
            ),
        }
    report = {
        "status": "PARTIAL_TECHNICAL_EVALUATION_T1_M4_NO_RISK_OUTPUTS",
        "equivalent_gate": "T1_EQUIVALENT_GATE_V1",
        "original_brd_gate": "NOT_ACCEPTED",
        "slice_documents": SLICES,
        "metrics": metrics,
        "prediction_module": "app.clause.segmenter.segment",
        "segmenter_version": SEGMENTATION_VERSION,
        "gold_access_order": (
            "D1 Dev Gold used to fit M7; T1 clean reference coordinates read as input. "
            "T1/T2 Test labels and citations opened only after predictions; restricted "
            "prediction artifact saved after scoring."
        ),
        "bootstrap": {"iterations": 1000, "seed": 0, "cluster_unit": "document"},
        "limitation": (
            "HDLD014 is synthetic. M7 uses a new fixed D1-only 1-NN baseline rather than a "
            "pre-existing W5 classifier. T1 M4 has no emitted risk outputs to score. "
            "T2 privacy reference is derived and not independently adjudicated. "
            "Technical scores do not establish original BRD or MS-4 acceptance."
        ),
    }
    report["versions"] = {"corpus_version": corpus.corpus_version, "data_graph_version": corpus.graph_version}
    report["input_sha256"] = {
        "equivalent_gate_receipt": digest(data_root / "data/intake/t1_equivalent_gate_signoff_2026-11-06.json"),
        "T1_segmentation_gold": digest(restricted / "T1_segmentation_gold_v01/manifest.json"),
        "T1_clause_label_gold": digest(restricted / "T1_clause_label_gold_v01/manifest.json"),
        "T1_privacy_gold": digest(restricted / "T1_privacy_gold_v01/manifest.json"),
        "T2_segmentation_gold": digest(restricted / "T2_segmentation_gold_v01/manifest.json"),
        "T2_injection_gold": digest(restricted / "T2_injection_gold_v01/manifest.json"),
        "synthetic_control_gold": digest(restricted / "HDLD014_synthetic_control_gold_v01/manifest.json"),
        "corpus_manifest": digest(corpus_path / "manifest.yaml"),
        "data_graph": digest(corpus_path / "edges.jsonl"),
        "evaluation_script": digest(Path(__file__)),
        "m5_dev_rule_module": digest(
            Path(__file__).resolve().parents[1] / "backend/app/risk/dev_injection_baseline.py"
        ),
        "m5_dev_rule_source": digest(data_root / "scripts/augment_d2_m5_art17_predictions.py"),
        "m7_dev_training_clauses": digest(d1_source),
        "m7_dev_training_gold": digest(d1_gold_root / "manifest.json"),
        "m7_dev_model_module": digest(Path(__file__).resolve().parents[1] / "backend/app/clause/dev_tfidf_baseline.py"),
        "m7_genuine_reference_spans": digest(clean_path),
        "m4_quote_metric_module": digest(
            Path(__file__).resolve().parents[1] / "ai_pipeline/evaluation/metrics/quote_span.py"
        ),
    }
    full_labels = {}
    for doc in SLICES["slice_t1_real_9"]:
        gold = json.loads(
            (restricted / "T1_clause_label_gold_v01" / f"{doc}.gold_clause_labels.json").read_text(encoding="utf-8")
        )
        full_labels[doc] = len(gold["items"])
    with clean_path.open(encoding="utf-8-sig", newline="") as stream:
        clean_rows = list(csv.DictReader(stream))
    clean_counts = {doc: sum(row["contract_id"] == doc for row in clean_rows) for doc in SLICES["slice_t1_real_9"]}
    for slice_name, docs in SLICES.items():
        if slice_name == "T2":
            metrics[slice_name]["gold_scope"] = {"documents": 9, "segmentation_spans": 872, "injected_cases": 30}
        else:
            metrics[slice_name]["gold_scope"] = {
                "documents": len(docs),
                "full_label_rows": sum(full_labels.get(doc, 10 if doc == "HDLD014" else 0) for doc in docs),
                "genuine_clause_rows": sum(clean_counts.get(doc, 10 if doc == "HDLD014" else 0) for doc in docs),
                "synthetic_control_rows": 10 if "HDLD014" in docs else 0,
            }
            cases = []
            for doc in docs:
                folder = (
                    restricted / "HDLD014_synthetic_control_gold_v01"
                    if doc == "HDLD014"
                    else restricted / "T1_clause_label_gold_v01"
                )
                labels = json.loads((folder / f"{doc}.gold_clause_labels.json").read_text(encoding="utf-8"))["items"]
                for row in labels:
                    clause_id = row["clause_id"]
                    if clause_id not in m7_predictions[doc]:
                        raise ValueError(f"missing independent M7 prediction for {clause_id}")
                    cases.append(
                        (
                            doc,
                            ClauseClassificationCase(
                                clause_id,
                                row["labels"],
                                m7_predictions[doc][clause_id],
                            ),
                        )
                    )
            genuine_cases = []
            for row in clean_rows:
                doc = row["contract_id"]
                if doc not in docs:
                    continue
                start, end = int(row["start_offset"]), int(row["end_offset"])
                if clean_source_text[doc][start:end] != row["clause_text"]:
                    raise ValueError(f"genuine Gold text no longer matches raw source for {doc}")
                genuine_cases.append(
                    (
                        doc,
                        ClauseClassificationCase(
                            row["clause_id"],
                            (row["clause_type"],),
                            m7_clean_predictions[doc][row["clause_id"]],
                        ),
                    )
                )
            if "HDLD014" in docs:
                genuine_cases.extend((doc, case) for doc, case in cases if doc == "HDLD014")
            for subset, selected_cases in (("full", cases), ("genuine", genuine_cases)):
                point = evaluate_clause_classification(row for _, row in selected_cases)
                direct = macro_f1_sampled(row for _, row in selected_cases)
                if direct is None or point.macro_f1 is None or abs(direct - point.macro_f1) > 1e-12:
                    raise ValueError("M7 bootstrap scorer diverges from pipeline point estimator")
                clusters = {doc: [row for source, row in selected_cases if source == doc] for doc in docs}
                ci = bootstrap_cluster_interval(clusters, macro_f1_sampled, iterations=1000, random_seed=0)
                metrics[slice_name][f"M7_{subset}"] = {
                    "status": "TECHNICAL_SCORE",
                    "score": point.macro_f1,
                    "rows": point.total_clauses,
                    "macro_class_count": point.macro_class_count,
                    "ci95": {
                        "low": ci.low,
                        "high": ci.high,
                        "iterations": 1000,
                        "seed": 0,
                        "cluster_count": ci.cluster_count,
                        "valid_replicates": ci.valid_replicate_count,
                    },
                    "prediction_module": "app.clause.dev_tfidf_baseline.DevTfidfBaseline",
                    "training_scope": "D1 Gold, HDLD001-004, 183 clauses, fixed character ngram TF-IDF 1-NN",
                }
            metrics[slice_name]["M7"] = metrics[slice_name]["M7_full"]
    for entry in metrics.values():
        for name in ("M3a", "M4", "M5", "M7", "M8"):
            if name in entry:
                continue
            reasons = {
                "M3a": "No independently generated T1/T2 citation decisions with retrieval trace.",
                "M4": "No adjudicated T2 privacy spans on the injected canonical documents.",
                "M5": "No callable frozen T2 risk predictor; injection Gold cannot be reused as predictions.",
                "M7": "No callable frozen independent clause classifier; Data v01/v02/v03 proposals are excluded.",
                "M8": "No independently predicted T2 clause labels and paired graph retrieval candidates.",
            }
            entry[name] = {"status": "NOT_RUN", "score": None, "ci95": None, "reason": reasons[name]}
    for name in SLICES:
        if name == "T2":
            metrics[name]["M7"] = {
                "status": "NOT_APPLICABLE",
                "reason": "T2 has injection and segmentation Gold, but no independent clause-label Gold.",
            }
        else:
            for metric in ("M5", "M8"):
                metrics[name][metric] = {
                    "status": "NOT_APPLICABLE",
                    "reason": "Injected-error recall and paired retrieval are measured on T2 cases.",
                }
    return predicted, derived_privacy, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prediction_path = args.data_root / "data/intake/restricted/T1_T2_equivalent_gate_m1_predictions_v01.json"
    if args.output.exists():
        old_report = json.loads(args.output.read_text(encoding="utf-8"))
        if old_report.get("equivalent_gate") != "T1_EQUIVALENT_GATE_V1":
            raise FileExistsError("unrelated report already exists")
    if prediction_path.exists():
        old_predictions = json.loads(prediction_path.read_text(encoding="utf-8"))
        expected_keys = {f"T1/{doc}" for doc in SLICES["slice_composite_10"]} | {f"T2/{doc}" for doc in SLICES["T2"]}
        if set(old_predictions) != expected_keys:
            raise FileExistsError("unrelated prediction artifact already exists")
    predictions, derived_privacy, report = evaluate(args.data_root)
    serializable = {f"{dataset}/{doc}": value for (dataset, doc), value in predictions.items()}
    prediction_path.write_text(json.dumps(serializable, indent=2) + "\n", encoding="utf-8")
    report["predictions_sha256"] = digest(prediction_path)
    reference_path = args.data_root / "data/intake/restricted/T2_privacy_derived_reference_v01.json"
    if reference_path.exists():
        old_reference = json.loads(reference_path.read_text(encoding="utf-8"))
        if old_reference.get("status") != "DERIVED_TECHNICAL_REFERENCE_NOT_HUMAN_ADJUDICATED":
            raise FileExistsError("unrelated T2 privacy reference already exists")
    reference_path.write_text(
        json.dumps(
            {
                "status": "DERIVED_TECHNICAL_REFERENCE_NOT_HUMAN_ADJUDICATED",
                "method": "Exact T2-to-T1 restoration and offset projection across newline envelopes",
                "documents": derived_privacy,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    report["input_sha256"]["T2_privacy_derived_reference"] = digest(reference_path)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: {"M1": value["M1"]} for key, value in report["metrics"].items()}))


if __name__ == "__main__":
    main()
