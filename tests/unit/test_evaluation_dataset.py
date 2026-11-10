import json

import pytest

from ai_pipeline.evaluation.dataset import _validate_privacy_gold, load_dataset


def test_privacy_gold_accepts_adjudicated_metadata_only_spans():
    artifact = {
        "schema_version": "privacy_gold_v1", "status": "GOLD_ADJUDICATED", "source": "synthetic review",
        "offset_unit": "unicode_code_point",
        "pii_spans": [{"start_char": 1, "end_char": 5, "pii_type": "EMAIL"}],
        "preserve_spans": [{"start_char": 8, "end_char": 12, "field": "WAGE"}],
    }
    _validate_privacy_gold(artifact)

    with pytest.raises(ValueError, match="required metadata fields"):
        _validate_privacy_gold({**artifact, "text": "private source"})
    with pytest.raises(ValueError, match="not adjudicated"):
        _validate_privacy_gold({**artifact, "status": "AI_CANDIDATE_NEEDS_REVIEW"})
    with pytest.raises(ValueError, match="unknown pii_type"):
        _validate_privacy_gold({**artifact, "pii_spans": [{"start_char": 1, "end_char": 5, "pii_type": "UNKNOWN"}]})
    with pytest.raises(ValueError, match="integer range"):
        _validate_privacy_gold({**artifact, "pii_spans": [{"start_char": True, "end_char": 5, "pii_type": "EMAIL"}]})


@pytest.fixture
def valid_manifest(tmp_path):
    (tmp_path / "contracts").mkdir()
    (tmp_path / "gold").mkdir()
    (tmp_path / "contracts" / "doc1.txt").write_text("Synthetic contract", encoding="utf-8")
    artifacts = {
        "seg.json": {"segments": []},
        "clause.json": {"clauses": []},
        "risk.json": {"risks": []},
        "injected.json": {"injections": []},
        "privacy.json": {
            "schema_version": "privacy_gold_v1", "status": "GOLD_ADJUDICATED", "source": "synthetic review",
            "offset_unit": "unicode_code_point", "pii_spans": [], "preserve_spans": [],
        },
    }
    for name, artifact in artifacts.items():
        (tmp_path / "gold" / name).write_text(json.dumps(artifact), encoding="utf-8")
    manifest = {
        "dataset": "SYNTH",
        "dataset_version": "synth_v1",
        "documents": [{
            "doc_id": "doc1",
            "file": "contracts/doc1.txt",
            "role_variants": ["EMPLOYEE", "EMPLOYER"],
            "gold_segmentation": "gold/seg.json",
            "gold_clause_labels": "gold/clause.json",
            "gold_risks": "gold/risk.json",
            "injected_errors": "gold/injected.json",
            "privacy_gold": "gold/privacy.json",
        }],
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path, manifest


def test_load_dataset_resolves_source_and_gold_artifacts(valid_manifest):
    path, _ = valid_manifest

    dataset = load_dataset(path)

    assert (dataset.dataset, dataset.dataset_version) == ("SYNTH", "synth_v1")
    assert len(dataset.documents) == 1
    document = dataset.documents[0]
    assert document.doc_id == "doc1"
    assert document.source_path == path.parent / "contracts" / "doc1.txt"
    assert document.role_variants == ("EMPLOYEE", "EMPLOYER")
    assert document.injected_errors == {"injections": []}


def test_manifest_duplicate_json_keys_are_rejected(valid_manifest):
    path, _ = valid_manifest
    path.write_text('{"dataset":"SYNTH","dataset":"OTHER","dataset_version":"v1","documents":[]}',
                    encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate JSON key: dataset"):
        load_dataset(path)


def test_gold_duplicate_json_keys_are_rejected(valid_manifest):
    path, _ = valid_manifest
    (path.parent / "gold" / "seg.json").write_text('{"segments":[],"segments":[]}', encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate JSON key: segments"):
        load_dataset(path)


def test_loader_rejects_draft_or_text_bearing_privacy_gold(valid_manifest):
    path, _ = valid_manifest
    privacy_path = path.parent / "gold" / "privacy.json"
    artifact = json.loads(privacy_path.read_text(encoding="utf-8"))
    for invalid in ({**artifact, "status": "AI_CANDIDATE_NEEDS_REVIEW"}, {**artifact, "text": "private source"}):
        privacy_path.write_text(json.dumps(invalid), encoding="utf-8")
        with pytest.raises(ValueError, match="privacy gold"):
            load_dataset(path)


def test_duplicate_document_ids_are_rejected(valid_manifest):
    path, manifest = valid_manifest
    manifest["documents"].append(dict(manifest["documents"][0]))
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="document IDs must be unique"):
        load_dataset(path)


def test_missing_artifact_file_is_rejected(valid_manifest):
    path, manifest = valid_manifest
    manifest["documents"][0]["gold_risks"] = "gold/missing.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="referenced file does not exist"):
        load_dataset(path)


def test_paths_cannot_escape_dataset_root(valid_manifest, tmp_path):
    path, manifest = valid_manifest
    outside = tmp_path.parent / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    manifest["documents"][0]["gold_risks"] = "../outside.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="path escapes dataset root"):
        load_dataset(path)


def test_duplicate_role_variants_are_rejected(valid_manifest):
    path, manifest = valid_manifest
    manifest["documents"][0]["role_variants"] = ["EMPLOYEE", "EMPLOYEE"]
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="role variants must be non-empty and unique"):
        load_dataset(path)
