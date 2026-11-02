from datetime import date

import pytest

from ai_pipeline.evaluation.runner import RetrievalRunInput, run_paired_m8


def test_paired_runner_uses_same_inputs_and_budget_with_graph_flag_only_changed():
    seen = []

    def retrieve(*, case, masked_text, predicted_labels, analysis_date, final_k, graph_enabled):
        seen.append((case, masked_text, predicted_labels, analysis_date, final_k, graph_enabled))
        return ("law:a",) if graph_enabled else ("law:b",)

    rows = (RetrievalRunInput("case-1", "masked clause", ("WAGE",), date(2025, 1, 1), "law:a"),)
    result = run_paired_m8(rows, retrieve, final_k=5)

    assert result.graph_off.recall == 0.0
    assert result.graph_on.recall == 1.0
    assert len(seen) == 2
    assert seen[0][:-1] == seen[1][:-1]
    assert (seen[0][-1], seen[1][-1]) == (False, True)


def test_paired_runner_rejects_missing_predicted_labels():
    with pytest.raises(ValueError, match="predicted_labels must be non-empty"):
        RetrievalRunInput("case-1", "masked clause", (), date(2025, 1, 1), "law:a")


def test_paired_runner_rejects_callback_candidates_over_shared_budget():
    row = RetrievalRunInput("case-1", "masked clause", ("WAGE",), date(2025, 1, 1), "law:a")
    with pytest.raises(ValueError, match="exceeds final_k"):
        run_paired_m8((row,), lambda **_: ("law:a", "law:b"), final_k=1, k=1)


def test_paired_runner_rejects_duplicate_case_ids_before_running():
    row = RetrievalRunInput("case-1", "masked clause", ("WAGE",), date(2025, 1, 1), "law:a")
    with pytest.raises(ValueError, match="case_id values must be unique"):
        run_paired_m8((row, row), lambda **_: (), final_k=5)


def test_run_input_requires_date_not_datetime():
    from datetime import datetime

    with pytest.raises(ValueError, match="analysis_date must be a date"):
        RetrievalRunInput("case-1", "masked clause", ("WAGE",), datetime(2025, 1, 1), "law:a")
