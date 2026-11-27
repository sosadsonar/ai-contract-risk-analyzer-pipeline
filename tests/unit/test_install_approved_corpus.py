"""Private release installation must fail before writing on invalid input."""

import hashlib
import json
import shutil
from pathlib import Path

import pytest
import yaml
from app.domain.errors import LegalCorpusConflict
from app.legal.corpus_loader import load_corpus

from scripts.install_approved_corpus import install
from tests.unit.test_legal_corpus_v2_release import v2_dir  # noqa: F401

FIXTURE = Path(__file__).parents[1] / "fixtures/legal_corpus/valid"


def _input(tmp_path):
    source = tmp_path / "source"
    shutil.copytree(FIXTURE, source)
    manifest = {
        "corpus_version": "fixture_v1", "graph_version": "fixture_graph_v1",
        "timezone": "Asia/Ho_Chi_Minh", "release_status": "APPROVED",
        "checksums": {name: hashlib.sha256((source / name).read_bytes()).hexdigest()
                      for name in ("provisions.jsonl", "edges.jsonl", "label_map.yaml")},
    }
    (source / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    metadata = {
        "corpus_version": manifest["corpus_version"],
        "graph_version": manifest["graph_version"],
        "usage_scope": "INTERNAL_REPO_ONLY",
        "release_checksums": {
            name: hashlib.sha256((source / name).read_bytes()).hexdigest()
            for name in ("provisions.jsonl", "edges.jsonl", "label_map.yaml")
        },
    }
    meta = tmp_path / "metadata.json"
    meta.write_text(json.dumps(metadata), encoding="utf-8")
    return source, meta


def test_installs_exact_bytes_only_inside_private_directory(tmp_path):
    source, meta = _input(tmp_path)
    private = tmp_path / ".local"
    target = private / "corpus"
    result = install(source, target, meta, private)
    assert result["release_status"] == "APPROVED"
    assert (target / "provisions.jsonl").read_bytes() == (source / "provisions.jsonl").read_bytes()


def test_changed_bytes_rejected_without_creating_destination(tmp_path):
    source, meta = _input(tmp_path)
    (source / "edges.jsonl").write_bytes(b"tampered")
    private = tmp_path / ".local"
    with pytest.raises(ValueError, match="checksum"):
        install(source, private / "corpus", meta, private)
    assert not (private / "corpus").exists()


def test_existing_output_and_marker_are_preserved(tmp_path):
    source, meta = _input(tmp_path)
    private = tmp_path / ".local"
    target = private / "corpus"
    target.mkdir(parents=True)
    marker = target / "marker"
    marker.write_bytes(b"keep")
    with pytest.raises(FileExistsError):
        install(source, target, meta, private)
    assert marker.read_bytes() == b"keep"


def test_destination_outside_private_directory_rejected(tmp_path):
    source, meta = _input(tmp_path)
    with pytest.raises(ValueError, match="private"):
        install(source, tmp_path / "public", meta, tmp_path / ".local")


def test_graph_version_mismatch_rejected(tmp_path):
    source, meta = _input(tmp_path)
    metadata = json.loads(meta.read_text(encoding="utf-8"))
    metadata["graph_version"] = "different"
    meta.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ValueError, match="version"):
        install(source, tmp_path / ".local/corpus", meta, tmp_path / ".local")


@pytest.mark.parametrize("omit_receipt", [False, True])
def test_installer_validates_the_same_bytes_it_installs(v2_dir, omit_receipt):  # noqa: F811
    manifest = yaml.safe_load((v2_dir / "manifest.yaml").read_text(encoding="utf-8"))
    checksums = dict(manifest["checksums"])
    if omit_receipt:
        del checksums["review_receipts.json"]
    metadata = v2_dir / "metadata.json"
    metadata.write_text(json.dumps({
        "corpus_version": manifest["corpus_version"], "graph_version": manifest["graph_version"],
        "usage_scope": "INTERNAL_REPO_ONLY", "release_checksums": checksums,
    }), encoding="utf-8")
    private = v2_dir / ".local"
    target = private / "corpus"
    if omit_receipt:
        with pytest.raises(LegalCorpusConflict, match="review_receipts"):
            install(v2_dir, target, metadata, private)
        assert not target.exists()
    else:
        install(v2_dir, target, metadata, private)
        assert load_corpus(target).release_status == "APPROVED"


def test_failed_write_removes_its_new_target(tmp_path, monkeypatch):
    source, metadata = _input(tmp_path)
    private = tmp_path / ".local"
    target = private / "corpus"
    original_open = Path.open

    def failing_open(path, mode="r", *args, **kwargs):
        if path == target / "manifest.yaml" and mode == "xb":
            raise OSError("injected output failure")
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", failing_open)
    with pytest.raises(OSError, match="injected output failure"):
        install(source, target, metadata, private)
    assert not target.exists()
