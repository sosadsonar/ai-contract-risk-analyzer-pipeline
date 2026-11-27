"""D2 derivatives must share the original D1 document's bootstrap cluster."""

import csv
import hashlib
import json
from pathlib import Path

import pytest

from scripts import measure_m8_dev as protocol
from tests.unit.test_data_graph import fake_corpus  # noqa: F401


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture
def synthetic_dev(tmp_path):
    root = tmp_path / "data/intake/restricted"
    training, lineage, derived = [], [], []
    for i, label_count in enumerate((46, 46, 46, 45), 1):
        doc = f"HDLD{i:03}"
        ref = f"{doc}_C1"
        source = f"{doc} Nội dung giả lập."
        digest = hashlib.sha256(source.encode()).hexdigest()
        for folder, suffix in (("D1_m1_runtime_predictions_v01", ".canonical_nfc.txt"), ("D2_candidate_v02", ".d2_candidate.txt")):
            target = root / folder / f"{doc}{suffix}"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.encode())
        geometry = {"source_sha256": digest, "segments": [{"gold_clause_ref": ref, "start_char": 0, "end_char": len(source)}]}
        for folder in ("D1_m1_gold_v01", "D2_segmentation_gold_v02"):
            _write(root / folder / f"{doc}.gold_segmentation.json", geometry)
        items = [{"clause_id": f"{doc}_C{n}", "labels": ["JOB_INFO"]} for n in range(1, label_count + 1)]
        training.extend({"contract_id": doc, "clause_id": row["clause_id"], "clause_text": source} for row in items)
        _write(root / f"D1_clause_label_gold_v01/{doc}.gold_clause_labels.json", {"items": items})
        gold = {"clause_id": ref, "gold_citation_id": "TESTLAW:art21:cl1:ptc"}
        _write(root / f"D1_m2_risk_gold_v03/{doc}.risk_gold.json", {"items": [gold] * (4 if i < 4 else 2)})
        _write(root / f"D2_injection_gold_v01/{doc}.injected_error_gold.json", {
            "injections": [{**gold, "verification": [{"decision": "VERIFIED"}]}] * (8 if i < 3 else 7),
        })
        lineage.append({"doc_id": doc, "source_d1_canonical_sha256": digest, "d2_candidate_canonical_sha256": digest})
        derived.append({"doc_id": doc, "canonical_sha256": digest})
    original = root / "D2_candidate_v01/manifest.json"
    _write(original, {"source_dataset": "D1", "documents": lineage})
    _write(root / "D2_candidate_v02/manifest.json", {
        "source_d2_manifest_sha256": hashlib.sha256(original.read_bytes()).hexdigest(), "documents": derived,
    })
    target = tmp_path / "data/processed/clauses_v06.csv"
    target.parent.mkdir(parents=True)
    with target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("contract_id", "clause_id", "clause_text"))
        writer.writeheader()
        writer.writerows(training)
    return tmp_path


def test_d1_and_d2_share_four_source_clusters_without_changing_hits(synthetic_dev, fake_corpus, monkeypatch):  # noqa: F811
    monkeypatch.setattr(protocol, "load_corpus", lambda _: fake_corpus)
    result = protocol.evaluate(synthetic_dev, Path("unused"))
    assert result["bootstrap_cluster_count"] == 4
    assert result["graph_off"]["hits"] == result["graph_on"]["hits"] == 74


def test_broken_manifest_lineage_is_rejected(synthetic_dev, fake_corpus, monkeypatch):  # noqa: F811
    monkeypatch.setattr(protocol, "load_corpus", lambda _: fake_corpus)
    path = synthetic_dev / "data/intake/restricted/D2_candidate_v02/manifest.json"
    value = json.loads(path.read_text())
    value["source_d2_manifest_sha256"] = "0" * 64
    _write(path, value)
    with pytest.raises(ValueError, match="lineage"):
        protocol.evaluate(synthetic_dev, Path("unused"))


def test_wrong_original_document_binding_is_rejected(synthetic_dev, fake_corpus, monkeypatch):  # noqa: F811
    monkeypatch.setattr(protocol, "load_corpus", lambda _: fake_corpus)
    original = synthetic_dev / "data/intake/restricted/D2_candidate_v01/manifest.json"
    value = json.loads(original.read_text())
    value["documents"][0]["source_d1_canonical_sha256"] = "0" * 64
    _write(original, value)
    derived = original.parents[1] / "D2_candidate_v02/manifest.json"
    value = json.loads(derived.read_text())
    value["source_d2_manifest_sha256"] = hashlib.sha256(original.read_bytes()).hexdigest()
    _write(derived, value)
    with pytest.raises(ValueError, match="source lineage"):
        protocol.evaluate(synthetic_dev, Path("unused"))


@pytest.mark.parametrize("enabled", [True, False])
def test_source_signal_setting_is_applied_and_reported(synthetic_dev, fake_corpus, monkeypatch, enabled):  # noqa: F811
    monkeypatch.setattr(protocol, "load_corpus", lambda _: fake_corpus)
    calls = []

    def signal(texts, predictions):
        calls.append(True)
        return predictions

    monkeypatch.setattr(protocol, "add_source_working_conditions", signal)
    result = protocol.evaluate(synthetic_dev, Path("unused"), source_working_conditions=enabled)
    assert bool(calls) is enabled
    assert result["predictor_config"]["source_working_conditions"] is enabled
