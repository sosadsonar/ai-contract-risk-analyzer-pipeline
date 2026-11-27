"""Synthetic fixtures only: source-bound Gold must precede a full Dev oracle."""

import csv
import hashlib
import json
from datetime import date
from pathlib import Path

import pytest
from app.domain.errors import LegalCorpusConflict

from scripts import measure_m8_dev as protocol
from tests.unit.test_data_graph import fake_corpus  # noqa: F401
from tests.unit.test_m8_source_clusters import synthetic_dev  # noqa: F401


def _save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def first_reviewed_clause_labels():
    return "JOB_INFO", ["JOB_INFO"]


@pytest.fixture
def bound_gold(tmp_path, first_reviewed_clause_labels):
    restricted = tmp_path / "restricted"
    gold = tmp_path / "gold_v1"
    packet = tmp_path / "owner.csv"
    rows, source_hashes, geometry_hashes, file_hashes = [], {}, {}, {}
    for number, count in enumerate((63, 63, 62, 62), 1):
        doc = f"HDLD{number:03}"
        source = restricted / f"D2_candidate_v02/{doc}.d2_candidate.txt"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("a" * 100, encoding="utf-8")
        segments, labels = [], []
        for index in range(count):
            ref = f"d2seg_{index+1:04}"
            segments.append({"gold_clause_ref": ref, "start_char": index, "end_char": index+1,
                             "offset_unit": "unicode_code_point"})
            packet_labels, exported_labels = (
                first_reviewed_clause_labels if number == 1 and index == 0 else ("JOB_INFO", ["JOB_INFO"])
            )
            labels.append({"clause_id": ref, "labels": exported_labels})
            rows.append({"document_id": doc, "d2_source_sha256": _sha(source),
                         "d2_gold_clause_ref": ref, "start_char": str(index), "end_char": str(index+1),
                         "span_sha256": hashlib.sha256(b"a").hexdigest(),
                         "adjudicated_labels": packet_labels, "taxonomy_version": "clause_taxonomy_v03",
                         "reviewer_n1": "Review Human", "reviewer_n2": "", "decision": "APPROVED",
                         "reviewed_on": date.today().isoformat()})
        geometry = restricted / f"D2_segmentation_gold_v02/{doc}.gold_segmentation.json"
        _save(geometry, {"source_sha256": _sha(source), "status": "ADJUDICATED_D2_GOLD_V02", "segments": segments})
        file = gold / f"{doc}.gold_clause_labels.json"
        _save(file, {"schema_version": "clause_labels_v1", "status": "GOLD_ADJUDICATED",
                     "approval_governance_mode": "OWNER_SINGLE_APPROVER_AI_ASSISTED_V1",
                     "taxonomy_version": "clause_taxonomy_v03", "items": labels})
        source_hashes[doc], geometry_hashes[doc], file_hashes[file.name] = _sha(source), _sha(geometry), _sha(file)
    with packet.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    _save(gold / "manifest.json", {
        "schema_version": "d2_clause_label_gold_manifest_v2", "dataset_version": "synthetic_gold_v1",
        "status": "GOLD_ADJUDICATED", "taxonomy_version": "clause_taxonomy_v03",
        "approval_governance_mode": "OWNER_SINGLE_APPROVER_AI_ASSISTED_V1",
        "documents": sorted(source_hashes), "items": 250, "packet_sha256": _sha(packet),
        "d2_sources_sha256": source_hashes, "d2_segmentation_sha256": geometry_hashes,
        "gold_files_sha256": file_hashes,
    })
    return restricted, gold, packet


def test_full_gold_requires_all_250_source_bound_labels(bound_gold):
    from ai_pipeline.evaluation.d2_clause_gold import load_d2_gold

    labels, meta = load_d2_gold(*bound_gold)
    assert sum(map(len, labels.values())) == 250
    assert meta["dataset_version"] == "synthetic_gold_v1"
    assert len(meta["input_sha256"]) == 6


@pytest.mark.parametrize("first_reviewed_clause_labels", [
    pytest.param((" TRAINING ; JOB_INFO ; LEAVE ", ["TRAINING", "JOB_INFO", "LEAVE"]), id="three-labels"),
    pytest.param((" OTHER ", ["OTHER"]), id="other-alone"),
])
def test_gold_accepts_packet_label_whitespace_trimmed_by_converter(bound_gold, first_reviewed_clause_labels):
    from ai_pipeline.evaluation.d2_clause_gold import load_d2_gold

    labels, _ = load_d2_gold(*bound_gold)
    assert labels["HDLD001"]["d2seg_0001"] == first_reviewed_clause_labels[1]


@pytest.mark.parametrize("mutation", ["gold_file", "packet", "geometry", "source", "mixed_other", "duplicate_ref"])
def test_tampered_or_invalid_gold_cannot_unlock_oracle(bound_gold, mutation):
    from ai_pipeline.evaluation.d2_clause_gold import load_d2_gold

    restricted, gold, packet = bound_gold
    if mutation in ("gold_file", "packet", "geometry", "source"):
        path = {"gold_file": gold / "HDLD001.gold_clause_labels.json", "packet": packet,
                "geometry": restricted / "D2_segmentation_gold_v02/HDLD001.gold_segmentation.json",
                "source": restricted / "D2_candidate_v02/HDLD001.d2_candidate.txt"}[mutation]
        path.write_bytes(path.read_bytes() + b" ")
    else:
        path = gold / "HDLD001.gold_clause_labels.json"
        value = json.loads(path.read_text())
        if mutation == "mixed_other":
            value["items"][0]["labels"] = ["OTHER", "JOB_INFO"]
        else:
            value["items"][1]["clause_id"] = value["items"][0]["clause_id"]
        _save(path, value)
        manifest = json.loads((gold / "manifest.json").read_text())
        manifest["gold_files_sha256"][path.name] = _sha(path)
        _save(gold / "manifest.json", manifest)
    with pytest.raises(ValueError):
        load_d2_gold(restricted, gold, packet)


def test_full_oracle_uses_d2_gold_without_retraining_primary(synthetic_dev, fake_corpus, monkeypatch):  # noqa: F811
    monkeypatch.setattr(protocol, "load_corpus", lambda _: fake_corpus)
    # Source/hash checks are independently covered above; this checks evaluation wiring only.
    labels = {f"HDLD{i:03}": {f"HDLD{i:03}_C1": ["JOB_INFO"]} for i in range(1, 5)}
    monkeypatch.setattr(protocol, "load_d2_gold", lambda *args: (labels, {"input_sha256": {}, "dataset_version": "synthetic"}), raising=False)
    old = protocol.evaluate(synthetic_dev, Path("unused"))
    new = protocol.evaluate(synthetic_dev, Path("unused"), d2_gold_dir=Path("gold"), d2_review_packet=Path("packet"))
    assert new["graph_off"] == old["graph_off"] and new["graph_on"] == old["graph_on"]
    assert new["m8_oracle_labels"]["total"] == 74
    assert new["oracle_label_coverage"] == {"D1": 14, "D2": 60}
    assert new["m8_oracle_by_dataset"]["D2"]["total"] == 60


@pytest.mark.parametrize("field,value", [("decision", "PENDING"), ("reviewer_n1", "Gemini"),
                                         ("reviewer_n2", "Another Person"), ("reviewed_on", "20261124")])
def test_manifest_hashes_do_not_replace_actual_owner_decisions(bound_gold, field, value):
    from ai_pipeline.evaluation.d2_clause_gold import load_d2_gold

    restricted, gold, packet = bound_gold
    with packet.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    rows[0][field] = value
    with packet.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    manifest = json.loads((gold / "manifest.json").read_text())
    manifest["packet_sha256"] = _sha(packet)
    _save(gold / "manifest.json", manifest)
    with pytest.raises(ValueError, match="Owner review"):
        load_d2_gold(restricted, gold, packet)


@pytest.mark.parametrize("gold,packet", [(Path("gold"), None), (None, Path("packet"))])
def test_oracle_requires_both_packet_and_gold_before_loading_data(tmp_path, gold, packet):
    with pytest.raises(ValueError, match="both"):
        protocol.evaluate(tmp_path, tmp_path, d2_gold_dir=gold, d2_review_packet=packet)


def test_draft_evaluation_is_opt_in_and_does_not_claim_runtime_approval(synthetic_dev, fake_corpus, monkeypatch):  # noqa: F811
    from dataclasses import replace

    draft = replace(fake_corpus, release_status="DRAFT")
    monkeypatch.setattr(protocol, "load_corpus", lambda *args, **kwargs: draft)
    with pytest.raises(LegalCorpusConflict):
        protocol.evaluate(synthetic_dev, Path("unused"))
    result = protocol.evaluate(synthetic_dev, Path("unused"), allow_draft_corpus=True)
    assert result["draft_dev_opt_in"] is True and result["corpus_release_status"] == "DRAFT"
    assert result["oracle_label_coverage"] == {"D1": 14, "D2": 0}
