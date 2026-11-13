"""C-12a: corpus integrity, effective dates, edges, provenance, and fail-closed draft."""

import hashlib
import json
import shutil
from pathlib import Path

import pytest
import yaml
from app.domain.errors import LegalCorpusConflict
from app.legal.citation_id import make_citation_id
from app.legal.corpus_loader import load_corpus

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "legal_corpus"
DATA = Path(__file__).resolve().parents[2] / "data" / "legal_corpus"
FILES = ("provisions.jsonl", "edges.jsonl", "label_map.yaml")


def _write_manifest(folder: Path, status: str = "APPROVED") -> None:
    manifest = {
        "corpus_version": "fixture_v1",
        "graph_version": "fixture_graph_v1",
        "timezone": "Asia/Ho_Chi_Minh",
        "release_status": status,
        "checksums": {name: hashlib.sha256((folder / name).read_bytes()).hexdigest() for name in FILES},
    }
    (folder / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")


@pytest.fixture
def valid_dir(tmp_path: Path) -> Path:
    for name in FILES:
        shutil.copyfile(FIX / "valid" / name, tmp_path / name)
    _write_manifest(tmp_path)
    return tmp_path


def _edit_row(root: Path, mutator) -> None:
    path = root / "provisions.jsonl"
    items = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]
    mutator(items)
    path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in items) + "\n", encoding="utf-8")
    _write_manifest(root)


def test_valid_corpus_and_deterministic_ids(valid_dir):
    corpus = load_corpus(valid_dir)
    assert len(corpus.provisions) == 4
    assert len(corpus.edges) == 1
    assert corpus.edges[0].edge_type == "REFERS_TO"
    assert corpus.provisions[2].citation_id == make_citation_id("TESTLAW", "21", "1", "c")
    assert corpus.label_map["JOB_INFO"]["TESTLAW:art21:cl1:ptc"] == 0.9


def test_approved_real_corpus_loads_with_pinned_content():
    corpus = load_corpus(DATA)
    assert corpus.release_status == "APPROVED"
    assert len(corpus.provisions) == 16
    assert len(corpus.edges) == 5
    assert corpus.graph_version == "data_graph_2026-11-13_v02"


def test_real_corpus_preserves_article14_and_adds_approved_manual_edges():
    corpus = load_corpus(DATA, allow_draft=True)
    provisions = {item.citation_id: item for item in corpus.provisions}
    expected = (
        "BLLD2019:art14:cl1",
        "BLLD2019:art14:cl2",
        "REFERS_TO",
        "MANUAL",
    )

    assert "khoản 2 Điều này" in provisions[expected[0]].content
    assert expected[1] in provisions
    edges = [
        (item.from_citation_id, item.to_citation_id, item.edge_type, item.origin)
        for item in corpus.edges
    ]
    assert expected in edges
    assert len(edges) == 5
    assert (
        "BLLD2019:art17:cl3", "BLLD2019:art21:cl1:ptc", "GUIDES", "MANUAL",
    ) in edges
    assert (
        "BLLD2019:art17:cl1", "BLLD2019:art17:cl2", "REFERS_TO", "MANUAL",
    ) in edges
    assert (
        "BLLD2019:art21:cl1:ptg", "BLLD2019:art17:cl2", "GUIDES", "MANUAL",
    ) in edges
    assert (
        "BLLD2019:art21:cl1:ptđ", "BLLD2019:art17:cl2", "GUIDES", "MANUAL",
    ) in edges


def test_invalid_overlap_is_rejected(valid_dir):
    extra = (FIX / "invalid_overlap" / "provision.jsonl").read_text(encoding="utf-8")
    with (valid_dir / "provisions.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(extra)
    _write_manifest(valid_dir)
    with pytest.raises(LegalCorpusConflict, match="overlapping versions"):
        load_corpus(valid_dir)


def test_sequential_versions_without_overlap_are_accepted(valid_dir):
    def modify(items):
        items[0]["effective_to"] = "2024-12-31"
        updated = items[0].copy()
        updated.update(version="v2", effective_from="2025-01-01", effective_to=None)
        items.append(updated)

    _edit_row(valid_dir, modify)
    assert len(load_corpus(valid_dir).provisions) == 5


def test_unknown_edge_endpoint_is_rejected(valid_dir):
    shutil.copyfile(FIX / "invalid_edge" / "edges.jsonl", valid_dir / "edges.jsonl")
    _write_manifest(valid_dir)
    with pytest.raises(LegalCorpusConflict, match="unknown citation endpoint"):
        load_corpus(valid_dir)


def test_parent_edges_cannot_be_manually_loaded(valid_dir):
    path = valid_dir / "edges.jsonl"
    path.write_text(json.dumps({
        "from_citation_id": "TESTLAW:art21", "to_citation_id": "TESTLAW:art21:cl1",
        "edge_type": "PARENT_OF", "origin": "AUTO",
    }) + "\n", encoding="utf-8")
    _write_manifest(valid_dir)
    with pytest.raises(LegalCorpusConflict, match="only verified MANUAL"):
        load_corpus(valid_dir)


@pytest.mark.parametrize("field,invalid", [
    ("citation_id", "TESTLAW:art20"),
    ("parent_path", ["TESTLAW", "art22"]),
    ("content", "Cafe\u0301"),
    ("effective_to", "2020-01-01"),
    ("effective_from", "2021-13-01"),
])
def test_invalid_provision_is_rejected(valid_dir, field, invalid):
    _edit_row(valid_dir, lambda items: items[0].__setitem__(field, invalid))
    with pytest.raises(LegalCorpusConflict):
        load_corpus(valid_dir)


@pytest.mark.parametrize("bad_map", [
    {"FAKE_LABEL": {"TESTLAW:art22": 1.0}},
    {"OTHER": {"TESTLAW:art999": 1.0}},
    {"OTHER": {"TESTLAW:art22": float("nan")}},
    {"OTHER": {"TESTLAW:art22": 1.5}},
])
def test_invalid_label_map_is_rejected(valid_dir, bad_map):
    (valid_dir / "label_map.yaml").write_text(yaml.safe_dump(bad_map), encoding="utf-8")
    _write_manifest(valid_dir)
    with pytest.raises(LegalCorpusConflict):
        load_corpus(valid_dir)


def test_checksums_prevent_silent_source_edits(valid_dir):
    with (valid_dir / "provisions.jsonl").open("a", encoding="utf-8") as handle:
        handle.write("{}\n")
    with pytest.raises(LegalCorpusConflict, match="SHA-256 mismatch"):
        load_corpus(valid_dir)


def test_suggestions_are_not_runtime_edges(valid_dir):
    (valid_dir / "edge_suggestions.jsonl").write_text(
        '{"edge_type":"PARENT_OF","unverified":true}\n', encoding="utf-8"
    )
    assert len(load_corpus(valid_dir).edges) == 1


def test_duplicate_json_keys_cannot_shadow_a_legal_clause(valid_dir):
    path = valid_dir / "provisions.jsonl"
    rows = path.read_text(encoding="utf-8").splitlines()
    rows[0] = rows[0].replace('"content":', '"content":"shadowed", "content":', 1)
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    _write_manifest(valid_dir)
    with pytest.raises(LegalCorpusConflict, match="duplicate JSON key"):
        load_corpus(valid_dir)


def test_duplicate_yaml_keys_cannot_shadow_label_weight(valid_dir):
    path = valid_dir / "label_map.yaml"
    path.write_text("JOB_INFO:\n  TESTLAW:art21:cl1:ptc: 0.9\n"
                    "JOB_INFO:\n  TESTLAW:art21:cl1:ptc: 0.0\n", encoding="utf-8")
    _write_manifest(valid_dir)
    with pytest.raises(LegalCorpusConflict, match="duplicate key"):
        load_corpus(valid_dir)


@pytest.mark.parametrize("bad_value", [None, 2021, "2021-01-01T00:00:00"])
def test_missing_or_invalid_effective_from_is_rejected(valid_dir, bad_value):
    _edit_row(valid_dir, lambda rows: rows[0].__setitem__("effective_from", bad_value))
    with pytest.raises(LegalCorpusConflict):
        load_corpus(valid_dir)


def test_non_array_parent_path_rejected(valid_dir):
    _edit_row(valid_dir, lambda rows: rows[0].__setitem__("parent_path", "TESTLAW:art21"))
    with pytest.raises(LegalCorpusConflict, match="parent_path must be an array"):
        load_corpus(valid_dir)
