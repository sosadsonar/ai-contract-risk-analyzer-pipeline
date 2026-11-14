"""V2 approval needs auditable receipts for every runtime legal item."""

import hashlib
import json
import shutil
from pathlib import Path

import pytest
import yaml
from app.domain.errors import LegalCorpusConflict
from app.legal.corpus_loader import load_corpus

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "legal_corpus" / "valid"
REAL = Path(__file__).resolve().parents[2] / "data" / "legal_corpus"
FILES = ("provisions.jsonl", "edges.jsonl", "label_map.yaml", "review_receipts.json")


def _reviewed(**extra):
    return {
        "reviewer_n2": "Nguyen A", "reviewer_independent": "Tran B",
        "reviewed_on": "2026-11-15", "decision": "APPROVED", **extra,
    }


def _bundle(root):
    provisions = [json.loads(line) for line in (root / "provisions.jsonl").read_text(encoding="utf-8").splitlines()]
    edges = [json.loads(line) for line in (root / "edges.jsonl").read_text(encoding="utf-8").splitlines()]
    label_map = yaml.safe_load((root / "label_map.yaml").read_text(encoding="utf-8"))
    return {
        "sources": [{
            "source_id": "TESTLAW", "document_id": "TESTLAW",
            "source_url": "https://example.gov.vn/law.pdf",
            "source_sha256": "a" * 64, "accessed_on": "2026-11-15",
            "rights_status": "APPROVED",
        }],
        "provisions": [_reviewed(
            citation_id=p["citation_id"], version=p["version"],
            content_sha256=hashlib.sha256(p["content"].encode("utf-8")).hexdigest(),
            source_id="TESTLAW", source_locator="page 1, Article 21",
            amendment_chain="Original text; no amendment in fixture",
            effective_from=p["effective_from"], effective_to=p["effective_to"],
        ) for p in provisions],
        "edges": [_reviewed(**edge, source_id="TESTLAW", source_locator="page 1") for edge in edges],
        "labels": [_reviewed(label=label, citation_id=cid, weight=weight,
                             source_id="TESTLAW", source_locator="page 1")
                   for label, weights in label_map.items() for cid, weight in weights.items()],
        "release": _reviewed(note="Fixture release sign-off"),
    }


def _manifest(root, status="APPROVED"):
    manifest = {
        "corpus_version": "legal_corpus_v2_fixture", "graph_version": "graph_v2_fixture",
        "timezone": "Asia/Ho_Chi_Minh", "release_status": status,
        "checksums": {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                      for name in FILES if (root / name).exists()},
    }
    (root / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")


@pytest.fixture
def v2_dir(tmp_path):
    for name in FILES[:3]:
        shutil.copyfile(FIX / name, tmp_path / name)
    (tmp_path / "review_receipts.json").write_text(
        json.dumps(_bundle(tmp_path), ensure_ascii=False), encoding="utf-8",
    )
    _manifest(tmp_path)
    return tmp_path


def test_v2_approved_requires_review_receipts(v2_dir):
    (v2_dir / "review_receipts.json").unlink()
    _manifest(v2_dir)
    with pytest.raises(LegalCorpusConflict, match="review_receipts"):
        load_corpus(v2_dir)


def test_v2_approved_receipts_cover_all_items(v2_dir):
    assert len(load_corpus(v2_dir).provisions) == 4


@pytest.mark.parametrize("mutation", [
    lambda b: b["provisions"].pop(),
    lambda b: b["provisions"][0].update(content_sha256="0" * 64),
    lambda b: b["provisions"][0].update(reviewer_independent="Nguyen A"),
    lambda b: b["provisions"][0].update(effective_from="2020-01-01"),
    lambda b: b["sources"][0].update(source_sha256="bad"),
    lambda b: b["edges"].clear(),
    lambda b: b["labels"].clear(),
    lambda b: b["release"].update(decision="PENDING"),
])
def test_v2_rejects_incomplete_or_unverified_review(v2_dir, mutation):
    bundle = json.loads((v2_dir / "review_receipts.json").read_text(encoding="utf-8"))
    mutation(bundle)
    (v2_dir / "review_receipts.json").write_text(json.dumps(bundle), encoding="utf-8")
    _manifest(v2_dir)
    with pytest.raises(LegalCorpusConflict):
        load_corpus(v2_dir)


def test_v2_receipt_checksum_rejects_silent_edit(v2_dir):
    with (v2_dir / "review_receipts.json").open("a", encoding="utf-8") as handle:
        handle.write(" ")
    with pytest.raises(LegalCorpusConflict, match="SHA-256 mismatch"):
        load_corpus(v2_dir)


def test_v2_draft_is_never_runtime_approved(v2_dir):
    _manifest(v2_dir, status="DRAFT")
    with pytest.raises(LegalCorpusConflict, match="awaits"):
        load_corpus(v2_dir)


def test_edge_requires_temporally_coexisting_endpoints(v2_dir):
    path = v2_dir / "provisions.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    rows[0]["effective_to"] = "2024-12-31"
    rows[-1]["effective_from"] = "2025-01-01"
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    bundle = _bundle(v2_dir)
    (v2_dir / "review_receipts.json").write_text(json.dumps(bundle), encoding="utf-8")
    _manifest(v2_dir)
    with pytest.raises(LegalCorpusConflict, match="no common effective interval"):
        load_corpus(v2_dir)


def test_v1_snapshot_cannot_be_rewritten_with_new_manifest_hash(tmp_path):
    for name in FILES[:3] + ("manifest.yaml",):
        shutil.copyfile(REAL / name, tmp_path / name)
    path = tmp_path / "provisions.jsonl"
    path.write_bytes(path.read_bytes() + b"\n")
    manifest = yaml.safe_load((tmp_path / "manifest.yaml").read_text(encoding="utf-8"))
    manifest["checksums"]["provisions.jsonl"] = hashlib.sha256(path.read_bytes()).hexdigest()
    (tmp_path / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    with pytest.raises(LegalCorpusConflict, match="immutable v1"):
        load_corpus(tmp_path)
