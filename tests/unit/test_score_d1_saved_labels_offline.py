"""Offline M7 scoring helpers reject missing labels and combine document counts."""

import pytest

from scripts.score_d1_saved_labels_offline import macro_from_results, prediction_labels


def test_labeled_prediction_requires_one_to_three_explicit_labels():
    assert prediction_labels({"clause_labels": ["JOB_INFO"]}) == ("JOB_INFO",)
    with pytest.raises(ValueError):
        prediction_labels({})
    with pytest.raises(ValueError):
        prediction_labels({"labels": []})


def test_document_confusion_counts_are_aggregated_before_macro_f1():
    first = {"per_label": {"A": {"support": 3, "tp": 2, "fp": 0, "fn": 1}}}
    second = {"per_label": {"A": {"support": 3, "tp": 1, "fp": 1, "fn": 2}}}
    assert macro_from_results([first, second]) == pytest.approx(0.6)
    assert macro_from_results([first]) is None
