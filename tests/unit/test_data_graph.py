"""C-13(a): structured canonical PARENT_OF + MANUAL graph, with date gating."""

from dataclasses import replace
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.domain.errors import LegalCorpusConflict
from app.legal.baseline_retriever import BaselineRetriever
from app.legal.corpus_loader import LegalCorpus, LegalProvision, load_corpus
from app.legal.data_graph import DataGraph, GraphNeighbor, GraphRelation, get_candidates

from tests.unit.test_legal_corpus import DATA, FILES, FIX, _write_manifest


@pytest.fixture
def fake_corpus(tmp_path: Path):
    for name in FILES:
        (tmp_path / name).write_bytes((FIX / "valid" / name).read_bytes())
    _write_manifest(tmp_path)
    return load_corpus(tmp_path)


def test_structural_hierarchy_and_manual_edges_have_correct_origin(fake_corpus):
    graph = DataGraph(fake_corpus)
    assert GraphRelation("TESTLAW:art21", "TESTLAW:art21:cl1", "PARENT_OF", "AUTO") in graph.relations
    assert GraphRelation("TESTLAW:art21:cl1", "TESTLAW:art21:cl1:ptc", "PARENT_OF", "AUTO") in graph.relations
    assert GraphRelation("TESTLAW:art22", "TESTLAW:art21", "REFERS_TO", "MANUAL") in graph.relations
    assert len(graph.relations) == 3


def test_real_draft_corpus_indexes_source_checked_article14_reference():
    graph = DataGraph(load_corpus(DATA, allow_draft=True), allow_draft=True)
    expected = GraphRelation(
        "BLLD2019:art14:cl1", "BLLD2019:art14:cl2", "REFERS_TO", "MANUAL",
    )

    assert expected in graph.relations
    assert GraphNeighbor("BLLD2019:art14:cl2", "REFERS_TO", "MANUAL", "FORWARD") in graph.neighbors(
        "BLLD2019:art14:cl1", as_of=date(2022, 1, 1),
    )


def test_traversal_retains_edge_direction_and_date_filter(fake_corpus):
    graph = DataGraph(fake_corpus)
    neighbors = graph.neighbors("TESTLAW:art21", as_of=date(2025, 1, 1))
    assert {(x.citation_id, x.edge_type, x.direction) for x in neighbors} == {
        ("TESTLAW:art21:cl1", "PARENT_OF", "FORWARD"),
        ("TESTLAW:art22", "REFERS_TO", "REVERSE"),
    }
    assert graph.neighbors("TESTLAW:art21", as_of=date(2020, 1, 1)) == ()


def test_expired_neighbor_not_traversed(fake_corpus):
    retired = LegalProvision(**{
        **vars(fake_corpus.provisions[-1]), "effective_to": date(2022, 12, 31),
    })
    corpus = LegalCorpus(**{
        **vars(fake_corpus), "provisions": (*fake_corpus.provisions[:-1], retired),
    })
    graph = DataGraph(corpus)
    assert all(x.citation_id != "TESTLAW:art22" for x in graph.neighbors(
        "TESTLAW:art21", as_of=date(2023, 1, 1)
    ))


def test_draft_requires_opt_in_and_only_curated_edges_enter_graph(fake_corpus):
    draft = replace(load_corpus(DATA), release_status="DRAFT")
    with pytest.raises(LegalCorpusConflict, match="awaits Data/Legal reviewer"):
        DataGraph(draft)
    assert DataGraph(draft, allow_draft=True).relations == (
        GraphRelation(
            "BLLD2019:art14:cl1", "BLLD2019:art14:cl2", "REFERS_TO", "MANUAL",
        ),
    )


def test_unknown_node_has_no_neighbors(fake_corpus):
    assert DataGraph(fake_corpus).neighbors("TESTLAW:art999", as_of=date(2025, 1, 1)) == ()


def test_expand_caps_neighbors_and_ranks_relevance(fake_corpus):
    retriever = BaselineRetriever(fake_corpus, seed_k=1, final_k=4)
    baseline = retriever.retrieve("", ["JOB_INFO"], as_of=date(2025, 1, 1))
    graph = DataGraph(fake_corpus)
    cfg = SimpleNamespace(RETRIEVAL_SEED_K=1, RETRIEVAL_FINAL_K=4,
                          GRAPH_MAX_NEIGHBORS_PER_SEED=1, GRAPH_MAX_CHILDREN_PER_SEED=1)
    result = graph.expand(baseline.seeds, baseline.baseline_pool, cfg, as_of=date(2025, 1, 1))
    assert len(result) <= 4
    assert result[0].citation_id == baseline.seeds[0].citation_id
    assert len({item.citation_id for item in result}) == len(result)


def test_expand_prefers_forward_refers_to_neighbor(fake_corpus, monkeypatch):
    retriever = BaselineRetriever(fake_corpus, seed_k=1, final_k=4)
    baseline = retriever.retrieve("", ["JOB_INFO"], as_of=date(2025, 1, 1))
    seed = baseline.seeds[0]
    candidates = [item for item in baseline.baseline_pool if item.citation_id != seed.citation_id]
    graph = DataGraph(fake_corpus)
    monkeypatch.setattr(graph, "neighbors", lambda *_args, **_kwargs: (
        GraphNeighbor(candidates[0].citation_id, "REFERS_TO", "MANUAL", "REVERSE"),
        GraphNeighbor(candidates[1].citation_id, "GUIDES", "MANUAL", "FORWARD"),
    ))
    cfg = SimpleNamespace(RETRIEVAL_FINAL_K=4, GRAPH_MAX_NEIGHBORS_PER_SEED=4,
                          GRAPH_MAX_CHILDREN_PER_SEED=2)
    result = graph.expand((seed,), baseline.baseline_pool, cfg, as_of=date(2025, 1, 1))
    assert result[0].citation_id == seed.citation_id
    assert result[1].citation_id == candidates[1].citation_id


def test_expand_applies_direction_bonus_before_citation_tiebreak(fake_corpus, monkeypatch):
    retriever = BaselineRetriever(fake_corpus, seed_k=1, final_k=4)
    baseline = retriever.retrieve("", ["JOB_INFO"], as_of=date(2025, 1, 1))
    seed = baseline.seeds[0]
    candidates = sorted(
        (item for item in baseline.baseline_pool if item.citation_id != seed.citation_id),
        key=lambda item: item.citation_id,
    )
    reverse_candidate, forward_candidate = candidates[0], candidates[-1]
    graph = DataGraph(fake_corpus)
    monkeypatch.setattr(graph, "neighbors", lambda *_args, **_kwargs: (
        GraphNeighbor(reverse_candidate.citation_id, "REFERS_TO", "MANUAL", "REVERSE"),
        GraphNeighbor(forward_candidate.citation_id, "REFERS_TO", "MANUAL", "FORWARD"),
    ))
    cfg = SimpleNamespace(RETRIEVAL_FINAL_K=4, GRAPH_MAX_NEIGHBORS_PER_SEED=4,
                          GRAPH_MAX_CHILDREN_PER_SEED=2)
    result = graph.expand((seed,), baseline.baseline_pool, cfg, as_of=date(2025, 1, 1))
    assert result[1].citation_id == forward_candidate.citation_id


def test_expand_uses_stable_citation_order_for_equal_graph_scores(fake_corpus, monkeypatch):
    retriever = BaselineRetriever(fake_corpus, seed_k=1, final_k=4)
    baseline = retriever.retrieve("", ["JOB_INFO"], as_of=date(2025, 1, 1))
    seed = baseline.seeds[0]
    candidates = [item for item in baseline.baseline_pool if item.citation_id != seed.citation_id]
    graph = DataGraph(fake_corpus)
    monkeypatch.setattr(graph, "neighbors", lambda *_args, **_kwargs: tuple(
        GraphNeighbor(item.citation_id, "GUIDES", "MANUAL", "FORWARD")
        for item in reversed(candidates[:2])
    ))
    cfg = SimpleNamespace(RETRIEVAL_FINAL_K=4, GRAPH_MAX_NEIGHBORS_PER_SEED=4,
                          GRAPH_MAX_CHILDREN_PER_SEED=2)
    result = graph.expand((seed,), baseline.baseline_pool, cfg, as_of=date(2025, 1, 1))
    assert [item.citation_id for item in result[1:3]] == sorted(
        item.citation_id for item in candidates[:2]
    )


def test_get_candidates_keeps_final_k_and_graph_off_returns_baseline(fake_corpus):
    retriever = BaselineRetriever(fake_corpus, seed_k=2, final_k=4)
    cfg = SimpleNamespace(RETRIEVAL_SEED_K=2, RETRIEVAL_FINAL_K=4,
                          GRAPH_MAX_NEIGHBORS_PER_SEED=4, GRAPH_MAX_CHILDREN_PER_SEED=2)
    baseline, fallback = get_candidates(retriever, None, "", ["JOB_INFO"], date(2025, 1, 1), cfg)
    assert len(baseline) == 4
    assert fallback is False
    graph_result, fallback = get_candidates(
        retriever, DataGraph(fake_corpus), "", ["JOB_INFO"], date(2025, 1, 1), cfg,
    )
    assert len(graph_result) == len(baseline)
    assert fallback is False


def test_graph_failure_falls_back_to_full_baseline_pool(fake_corpus):
    class BrokenGraph:
        def expand(self, *args, **kwargs):
            raise RuntimeError("index failure")

    retriever = BaselineRetriever(fake_corpus, seed_k=2, final_k=4)
    cfg = SimpleNamespace(RETRIEVAL_SEED_K=2, RETRIEVAL_FINAL_K=4,
                          GRAPH_MAX_NEIGHBORS_PER_SEED=4, GRAPH_MAX_CHILDREN_PER_SEED=2)
    result, fallback = get_candidates(
        retriever, BrokenGraph(), "", ["JOB_INFO"], date(2025, 1, 1), cfg,
    )
    expected = retriever.retrieve("", ["JOB_INFO"], as_of=date(2025, 1, 1)).baseline_pool
    assert result == expected
    assert fallback is True


def test_graph_off_flag_returns_baseline_without_expanding(fake_corpus):
    class BrokenGraph:
        def expand(self, *args, **kwargs):
            raise AssertionError("disabled graph must not be called")

    retriever = BaselineRetriever(fake_corpus, seed_k=2, final_k=4)
    cfg = SimpleNamespace(RETRIEVAL_SEED_K=2, RETRIEVAL_FINAL_K=4,
                          GRAPH_MAX_NEIGHBORS_PER_SEED=4, GRAPH_MAX_CHILDREN_PER_SEED=2,
                          DATA_GRAPH_ENABLED=False)
    result, fallback = get_candidates(
        retriever, BrokenGraph(), "", ["JOB_INFO"], date(2025, 1, 1), cfg,
    )
    expected = retriever.retrieve("", ["JOB_INFO"], as_of=date(2025, 1, 1)).baseline_pool
    assert result == expected
    assert fallback is False


def test_shared_neighbor_is_deduplicated_without_evicting_seeds(fake_corpus, monkeypatch):
    retriever = BaselineRetriever(fake_corpus, seed_k=2, final_k=4)
    baseline = retriever.retrieve("", ["JOB_INFO"], as_of=date(2025, 1, 1))
    seed_ids = {item.citation_id for item in baseline.seeds}
    shared = next(item for item in baseline.baseline_pool if item.citation_id not in seed_ids)
    graph = DataGraph(fake_corpus)
    monkeypatch.setattr(graph, "neighbors", lambda *_args, **_kwargs: (
        GraphNeighbor(shared.citation_id, "GUIDES", "MANUAL", "FORWARD"),
    ))
    cfg = SimpleNamespace(RETRIEVAL_FINAL_K=4, GRAPH_MAX_NEIGHBORS_PER_SEED=4,
                          GRAPH_MAX_CHILDREN_PER_SEED=2)
    result = graph.expand(baseline.seeds, baseline.baseline_pool, cfg, as_of=date(2025, 1, 1))
    ids = [item.citation_id for item in result]
    assert ids[:len(baseline.seeds)] == [item.citation_id for item in baseline.seeds]
    assert ids.count(shared.citation_id) == 1
    assert len(ids) == 4
    assert [item.rank for item in result] == [1, 2, 3, 4]


def test_baseline_retrieval_failure_is_not_swallowed_by_graph_fallback(fake_corpus):
    class BrokenRetriever:
        final_k = 4

        def retrieve(self, *args, **kwargs):
            raise RuntimeError("baseline index failure")

    cfg = SimpleNamespace(RETRIEVAL_SEED_K=2, RETRIEVAL_FINAL_K=4,
                          GRAPH_MAX_NEIGHBORS_PER_SEED=4, GRAPH_MAX_CHILDREN_PER_SEED=2)
    with pytest.raises(RuntimeError, match="baseline index failure"):
        get_candidates(BrokenRetriever(), DataGraph(fake_corpus), "", [], date(2025, 1, 1), cfg)


def test_expand_rejects_seed_missing_from_baseline_pool(fake_corpus):
    retriever = BaselineRetriever(fake_corpus, seed_k=1, final_k=4)
    baseline = retriever.retrieve("", ["JOB_INFO"], as_of=date(2025, 1, 1))
    cfg = SimpleNamespace(RETRIEVAL_SEED_K=1, RETRIEVAL_FINAL_K=4,
                          GRAPH_MAX_NEIGHBORS_PER_SEED=4, GRAPH_MAX_CHILDREN_PER_SEED=2)
    with pytest.raises(ValueError, match="seed must be in baseline pool"):
        DataGraph(fake_corpus).expand(
            baseline.seeds, baseline.baseline_pool[1:], cfg, as_of=date(2025, 1, 1),
        )


def test_expand_rejects_more_seeds_than_final_k(fake_corpus):
    retriever = BaselineRetriever(fake_corpus, seed_k=2, final_k=4)
    baseline = retriever.retrieve("", ["JOB_INFO"], as_of=date(2025, 1, 1))
    cfg = SimpleNamespace(RETRIEVAL_FINAL_K=1, GRAPH_MAX_NEIGHBORS_PER_SEED=4,
                          GRAPH_MAX_CHILDREN_PER_SEED=2)
    with pytest.raises(ValueError, match="seeds cannot exceed retrieval final_k"):
        DataGraph(fake_corpus).expand(
            baseline.seeds, baseline.baseline_pool, cfg, as_of=date(2025, 1, 1),
        )


def test_get_candidates_rejects_final_k_mismatch(fake_corpus):
    retriever = BaselineRetriever(fake_corpus, seed_k=2, final_k=4)
    cfg = SimpleNamespace(RETRIEVAL_SEED_K=2, RETRIEVAL_FINAL_K=2,
                          GRAPH_MAX_NEIGHBORS_PER_SEED=4, GRAPH_MAX_CHILDREN_PER_SEED=2)
    with pytest.raises(ValueError, match="RETRIEVAL_FINAL_K must match baseline retriever"):
        get_candidates(retriever, DataGraph(fake_corpus), "", ["JOB_INFO"], date(2025, 1, 1), cfg)


@pytest.mark.parametrize("cap_name,bad_value", [
    ("RETRIEVAL_FINAL_K", 0),
    ("RETRIEVAL_FINAL_K", True),
    ("GRAPH_MAX_NEIGHBORS_PER_SEED", 1.5),
    ("GRAPH_MAX_CHILDREN_PER_SEED", "2"),
])
def test_expand_rejects_invalid_caps(fake_corpus, cap_name, bad_value):
    retriever = BaselineRetriever(fake_corpus, seed_k=1, final_k=4)
    baseline = retriever.retrieve("", ["JOB_INFO"], as_of=date(2025, 1, 1))
    cfg = SimpleNamespace(RETRIEVAL_FINAL_K=4, GRAPH_MAX_NEIGHBORS_PER_SEED=4,
                          GRAPH_MAX_CHILDREN_PER_SEED=2)
    setattr(cfg, cap_name, bad_value)
    with pytest.raises(ValueError, match="retrieval and graph caps must be positive integers"):
        DataGraph(fake_corpus).expand(
            baseline.seeds, baseline.baseline_pool, cfg, as_of=date(2025, 1, 1),
        )


def test_graph_expands_neighbor_outside_baseline_pool(fake_corpus):
    retriever = BaselineRetriever(fake_corpus, seed_k=1, final_k=2)
    baseline = retriever.retrieve("", ["JOB_INFO"], as_of=date(2025, 1, 1))
    graph = DataGraph(fake_corpus)
    cfg = SimpleNamespace(RETRIEVAL_SEED_K=1, RETRIEVAL_FINAL_K=2,
                          GRAPH_MAX_NEIGHBORS_PER_SEED=4, GRAPH_MAX_CHILDREN_PER_SEED=2)
    assert "TESTLAW:art21:cl1" not in {p.citation_id for p in baseline.baseline_pool}
    result = graph.expand(baseline.seeds, baseline.baseline_pool, cfg, as_of=date(2025, 1, 1))
    assert "TESTLAW:art21:cl1" in {p.citation_id for p in result}


def test_expand_limits_parent_children_per_seed(fake_corpus, monkeypatch):
    retriever = BaselineRetriever(fake_corpus, seed_k=1, final_k=4)
    baseline = retriever.retrieve("", ["JOB_INFO"], as_of=date(2025, 1, 1))
    seed = baseline.seeds[0]
    candidates = [item for item in baseline.baseline_pool if item.citation_id != seed.citation_id]
    score_by_id = {
        "TESTLAW:art22": 0.49,
        "TESTLAW:art21": 0.48,
        "TESTLAW:art21:cl1": 0.47,
    }
    pool = tuple(replace(item, baseline_score=score_by_id[item.citation_id])
                 if item.citation_id in score_by_id else item
                 for item in baseline.baseline_pool)
    graph = DataGraph(fake_corpus)
    monkeypatch.setattr(graph, "neighbors", lambda *_args, **_kwargs: tuple(
        GraphNeighbor(item.citation_id, "PARENT_OF", "AUTO", "FORWARD")
        for item in candidates
    ))
    one_child_cfg = SimpleNamespace(RETRIEVAL_FINAL_K=4, GRAPH_MAX_NEIGHBORS_PER_SEED=4,
                                    GRAPH_MAX_CHILDREN_PER_SEED=1)
    two_children_cfg = SimpleNamespace(RETRIEVAL_FINAL_K=4, GRAPH_MAX_NEIGHBORS_PER_SEED=4,
                                       GRAPH_MAX_CHILDREN_PER_SEED=2)
    one_child = graph.expand((seed,), pool, one_child_cfg, as_of=date(2025, 1, 1))
    two_children = graph.expand((seed,), pool, two_children_cfg, as_of=date(2025, 1, 1))
    assert [item.citation_id for item in one_child[1:]] == [
        "TESTLAW:art22", "TESTLAW:art21", "TESTLAW:art21:cl1",
    ]
    assert [item.citation_id for item in two_children[1:]] == [
        "TESTLAW:art21", "TESTLAW:art22", "TESTLAW:art21:cl1",
    ]


def test_child_cap_prefers_baseline_relevance_over_graph_only_neighbor(fake_corpus, monkeypatch):
    retriever = BaselineRetriever(fake_corpus, seed_k=1, final_k=2)
    baseline = retriever.retrieve("", ["JOB_INFO"], as_of=date(2025, 1, 1))
    seed = baseline.seeds[0]
    in_pool_child = next(item for item in baseline.baseline_pool if item.citation_id != seed.citation_id)
    graph_only_id = "TESTLAW:art21:cl1"
    assert graph_only_id not in {item.citation_id for item in baseline.baseline_pool}
    pool = tuple(
        replace(item, baseline_score=0.2) if item.citation_id == in_pool_child.citation_id else item
        for item in baseline.baseline_pool
    )
    graph = DataGraph(fake_corpus)
    monkeypatch.setattr(graph, "neighbors", lambda *_args, **_kwargs: (
        GraphNeighbor(graph_only_id, "PARENT_OF", "AUTO", "FORWARD"),
        GraphNeighbor(in_pool_child.citation_id, "PARENT_OF", "AUTO", "FORWARD"),
    ))
    cfg = SimpleNamespace(RETRIEVAL_FINAL_K=2, GRAPH_MAX_NEIGHBORS_PER_SEED=4,
                          GRAPH_MAX_CHILDREN_PER_SEED=1)
    result = graph.expand((seed,), pool, cfg, as_of=date(2025, 1, 1))
    assert [item.citation_id for item in result] == [seed.citation_id, in_pool_child.citation_id]


def test_expand_limits_total_neighbors_per_seed(fake_corpus, monkeypatch):
    retriever = BaselineRetriever(fake_corpus, seed_k=1, final_k=4)
    baseline = retriever.retrieve("", ["JOB_INFO"], as_of=date(2025, 1, 1))
    seed = baseline.seeds[0]
    candidates = [item for item in baseline.baseline_pool if item.citation_id != seed.citation_id]
    score_by_id = {
        "TESTLAW:art22": 0.49,
        "TESTLAW:art21": 0.48,
        "TESTLAW:art21:cl1": 0.47,
    }
    pool = tuple(replace(item, baseline_score=score_by_id[item.citation_id])
                 if item.citation_id in score_by_id else item
                 for item in baseline.baseline_pool)
    graph = DataGraph(fake_corpus)
    monkeypatch.setattr(graph, "neighbors", lambda *_args, **_kwargs: tuple(
        GraphNeighbor(item.citation_id, "GUIDES", "MANUAL", "FORWARD")
        for item in candidates
    ))
    one_neighbor_cfg = SimpleNamespace(RETRIEVAL_FINAL_K=4, GRAPH_MAX_NEIGHBORS_PER_SEED=1,
                                       GRAPH_MAX_CHILDREN_PER_SEED=2)
    two_neighbors_cfg = SimpleNamespace(RETRIEVAL_FINAL_K=4, GRAPH_MAX_NEIGHBORS_PER_SEED=2,
                                        GRAPH_MAX_CHILDREN_PER_SEED=2)
    one_neighbor = graph.expand((seed,), pool, one_neighbor_cfg, as_of=date(2025, 1, 1))
    two_neighbors = graph.expand((seed,), pool, two_neighbors_cfg, as_of=date(2025, 1, 1))
    assert [item.citation_id for item in one_neighbor[1:]] == [
        "TESTLAW:art22", "TESTLAW:art21", "TESTLAW:art21:cl1",
    ]
    assert [item.citation_id for item in two_neighbors[1:]] == [
        "TESTLAW:art21", "TESTLAW:art22", "TESTLAW:art21:cl1",
    ]
