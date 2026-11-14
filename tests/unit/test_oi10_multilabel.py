"""SRS OI-10 (OPEN_ISSUES_HANDLE_v4 §3.4 C4, C4b): chính sách đa nhãn và tie-break alignment."""

import pytest
from app.ai.prompts.clause_v1 import build_system_prompt
from app.clause.taxonomy import validate_labels

from ai_pipeline.evaluation.metrics.alignment import greedy_align_spans


@pytest.mark.parametrize("labels", [["OTHER"], ["JOB_INFO", "WORKING_TIME"],
                                    ["JOB_INFO", "WORKING_TIME", "LEAVE"]])
def test_valid_label_sets(labels):
    assert validate_labels(labels) == labels


@pytest.mark.parametrize("labels", [["OTHER", "JOB_INFO"], ["JOB_INFO", "OTHER"],
                                    ["JOB_INFO", "WORKING_TIME", "LEAVE", "TRAINING"],
                                    ["JOB_INFO", "JOB_INFO"], []])
def test_invalid_label_sets(labels):
    with pytest.raises(ValueError):
        validate_labels(labels)


def test_prompt_states_other_is_exclusive():
    prompt = build_system_prompt()
    assert "OTHER" in prompt and "luôn đứng một mình" in prompt


def test_greedy_iou_descending_first():
    # gold 0 overlaps pred 1 better than pred 0
    assert greedy_align_spans([(0, 10)], [(0, 6), (0, 9)]) == [(0, 1)]


def test_tie_break_gold_start_then_pred_start_not_input_order():
    gold = [(10, 20), (0, 10)]          # input order ≠ start order
    pred = [(0, 20)]                     # IoU 0.5 với cả hai gold
    assert greedy_align_spans(gold, pred) == [(1, 0)]  # gold có start nhỏ hơn thắng
    gold = [(0, 20)]
    pred = [(10, 20), (0, 10)]
    assert greedy_align_spans(gold, pred) == [(0, 1)]  # pred có start nhỏ hơn thắng


def test_each_span_matched_once():
    pairs = greedy_align_spans([(0, 10), (0, 10)], [(0, 10)])
    assert pairs == [(0, 0)]
