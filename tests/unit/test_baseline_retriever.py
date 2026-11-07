"""C-12b: same final_k pool with or without graph, effective dates, lexical weights."""

import shutil
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from app.domain.errors import LegalCorpusConflict
from app.legal.baseline_retriever import BaselineRetriever
from app.legal.corpus_loader import LegalCorpus, LegalProvision, load_corpus

from tests.unit.test_legal_corpus import DATA, FILES, FIX, _write_manifest


@pytest.fixture
def valid_dir(tmp_path: Path) -> Path:
    for name in FILES:
        shutil.copyfile(FIX / "valid" / name, tmp_path / name)
    _write_manifest(tmp_path)
    return tmp_path


def test_pool_contains_backups_beyond_graph_seeds(valid_dir):
    corpus = load_corpus(valid_dir)
    retriever = BaselineRetriever(corpus, seed_k=2, final_k=4)
    result = retriever.retrieve("Phụ lục", ["JOB_INFO"], as_of=date(2025, 1, 1))
    assert len(result.baseline_pool) == 4
    assert result.seeds == result.baseline_pool[:2]
    assert [c.rank for c in result.baseline_pool] == [1, 2, 3, 4]
    assert all(c.origin == "BASELINE_BACKUP" for c in result.baseline_pool[2:])
    assert len({c.citation_id for c in result.baseline_pool}) == 4


def test_label_score_direct_weight_and_bm25_normalized(valid_dir):
    corpus = load_corpus(valid_dir)
    candidates = BaselineRetriever(corpus).retrieve(
        "", ["JOB_INFO", "OTHER"], as_of=date(2025, 1, 1)
    ).baseline_pool
    by_id = {item.citation_id: item for item in candidates}
    assert by_id["TESTLAW:art21:cl1:ptc"].baseline_score == pytest.approx(0.70 * 0.9)
    assert by_id["TESTLAW:art22"].baseline_score == pytest.approx(0.70 * 0.5)
    assert all(item.bm25_normalized == 0 for item in candidates)


def test_lexical_match_contributes_to_score(valid_dir):
    corpus = load_corpus(valid_dir)
    result = BaselineRetriever(corpus).retrieve("Phụ lục", ["JOB_INFO"], as_of=date(2022, 1, 1))
    art22 = next(item for item in result.baseline_pool if item.citation_id == "TESTLAW:art22")
    assert art22.bm25_normalized > 0
    assert art22.baseline_score == pytest.approx(0.30 * art22.bm25_normalized)


def test_effective_date_filters_and_versions_are_deduped(valid_dir):
    original = load_corpus(valid_dir)
    first = original.provisions[0]
    old = LegalProvision(**{**vars(first), "effective_to": date(2023, 12, 31)})
    new = LegalProvision(**{**vars(first), "version": "v2", "effective_from": date(2024, 1, 1)})
    corpus = LegalCorpus(**{**vars(original), "provisions": (old, new, *original.provisions[1:])})
    retriever = BaselineRetriever(corpus, final_k=8)
    assert retriever.retrieve("anything", ["OTHER"], as_of=date(2020, 1, 1)).baseline_pool == ()
    old_result = retriever.retrieve("", ["JOB_INFO"], as_of=date(2023, 12, 31))
    new_result = retriever.retrieve("", ["JOB_INFO"], as_of=date(2024, 1, 1))
    assert sum(c.citation_id == first.citation_id for c in new_result.baseline_pool) == 1
    assert next(c for c in old_result.baseline_pool if c.citation_id == first.citation_id).version == "v1"
    assert next(c for c in new_result.baseline_pool if c.citation_id == first.citation_id).version == "v2"


def test_draft_corpus_retriever_is_blocked_by_default():
    draft = replace(load_corpus(DATA), release_status="DRAFT")
    with pytest.raises(LegalCorpusConflict, match="awaits Data/Legal reviewer"):
        BaselineRetriever(draft)
    assert BaselineRetriever(draft, allow_draft=True).retrieve(
        "lương", ["COMPENSATION_BENEFITS"], as_of=date(2022, 1, 1)
    ).baseline_pool


@pytest.mark.parametrize("invalid", [0, -1, True, 3.5])
def test_invalid_k_values_are_rejected(valid_dir, invalid):
    with pytest.raises(ValueError):
        BaselineRetriever(load_corpus(valid_dir), seed_k=invalid)


def test_unknown_label_and_non_date_rejected(valid_dir):
    retriever = BaselineRetriever(load_corpus(valid_dir))
    with pytest.raises(ValueError):
        retriever.retrieve("abc", ["UNKNOWN"], as_of=date(2025, 1, 1))
    with pytest.raises(ValueError):
        retriever.retrieve("abc", ["OTHER"], as_of="2025-01-01")
