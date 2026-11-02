import pytest

from ai_pipeline.eval.metrics.retrieval import RetrievalCase, evaluate_retrieval


def test_recall_at_k_compares_paired_graph_runs_and_added_candidates():
    cases = (
        RetrievalCase("e1", "law:art1", ("law:art1",), ("law:art2", "law:art1")),
        RetrievalCase("e2", "law:art3", ("law:art2",), ("law:art3", "law:art2")),
    )
    result = evaluate_retrieval(cases, final_k=5)

    assert result.k == 5
    assert result.final_k == 5
    assert (result.graph_off.hits, result.graph_off.total, result.graph_off.recall) == (1, 2, 0.5)
    assert (result.graph_on.hits, result.graph_on.total, result.graph_on.recall) == (2, 2, 1.0)
    assert result.graph_added_candidate_count == 2


def test_recall_only_counts_gold_within_k():
    case = RetrievalCase("e1", "law:art6", (
        "law:art1", "law:art2", "law:art3", "law:art4", "law:art5", "law:art6",
    ), ("law:art1", "law:art2", "law:art3", "law:art4", "law:art5", "law:art6"))
    result = evaluate_retrieval((case,), final_k=6, k=5)

    assert result.graph_off.hits == result.graph_on.hits == 0
    assert result.graph_off.recall == result.graph_on.recall == 0.0


def test_empty_cases_cannot_be_reported_as_perfect_recall():
    with pytest.raises(ValueError, match="at least one case"):
        evaluate_retrieval((), final_k=5)


def test_duplicate_case_ids_are_rejected():
    case = RetrievalCase("e1", "law:art1", ("law:art1",), ("law:art1",))
    with pytest.raises(ValueError, match="case_id values must be unique"):
        evaluate_retrieval((case, case), final_k=5)


@pytest.mark.parametrize("candidate_ids", [
    ("law:art1", "law:art1"),
    ("law:art1", " "),
])
def test_invalid_or_duplicate_candidate_ids_are_rejected(candidate_ids):
    case = RetrievalCase("e1", "law:art1", candidate_ids, ("law:art1",))
    with pytest.raises(ValueError, match="candidate citation IDs must be non-empty and unique"):
        evaluate_retrieval((case,), final_k=5)


def test_gold_citation_id_must_be_non_empty():
    case = RetrievalCase("e1", " ", ("law:art1",), ("law:art1",))
    with pytest.raises(ValueError, match="gold citation ID must be non-empty"):
        evaluate_retrieval((case,), final_k=5)


def test_candidate_lists_cannot_exceed_final_k():
    case = RetrievalCase("e1", "law:art1", ("law:art1", "law:art2"), ("law:art1",))
    with pytest.raises(ValueError, match="candidate list exceeds final_k"):
        evaluate_retrieval((case,), final_k=1, k=1)


def test_both_candidate_runs_are_required_per_case():
    case = RetrievalCase("e1", "law:art1", ("law:art1",), None)
    with pytest.raises(ValueError, match="candidate citation IDs must be a sequence"):
        evaluate_retrieval((case,), final_k=5)


def test_k_cannot_exceed_final_k():
    case = RetrievalCase("e1", "law:art1", ("law:art1",), ("law:art1",))
    with pytest.raises(ValueError, match="k must be between 1 and final_k"):
        evaluate_retrieval((case,), final_k=4, k=5)
