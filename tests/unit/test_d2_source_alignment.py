import hashlib
from difflib import SequenceMatcher

import pytest

from scripts.align_d2_source_labels import align_span, checked_geometry, classification_text_anchors


def _align(before, after, start, end, segments):
    return align_span(before, after, start, end, segments, SequenceMatcher(None, before, after, autojunk=False).get_matching_blocks())


def test_unchanged_subspan_retains_source_offsets_after_an_insertion():
    before = "abc original text xyz"
    after = "NEW abc original text xyz"
    result = _align(before, after, 8, 16, [{"ref": "D1_C1", "start": 4, "end": 17, "labels": ["JOB_INFO"]}])
    assert result["source_start_char"] == 4
    assert result["source_end_char"] == 12
    assert result["suggested_labels"] == ["JOB_INFO"]
    assert result["status"] == "UNCHANGED_CONTAINED_UNIT_REQUIRES_REVIEW"


def test_new_injection_gets_no_transferred_gold_label():
    result = _align("abcdef", "abc NEW def", 4, 7, [])
    assert result["status"] == "NEW_OR_CHANGED_SOURCE"
    assert result["suggested_labels"] == []


def test_repeated_text_is_not_treated_as_unique_evidence():
    result = _align("same text same text", "new same text same text", 4, 13, [])
    assert result["status"] == "AMBIGUOUS_REPEATED_SOURCE"


def test_merged_d1_units_require_review_instead_of_silently_choosing_a_label():
    source = "job and salary"
    segments = [{"ref": "A", "start": 0, "end": 3, "labels": ["JOB_INFO"]},
                {"ref": "B", "start": 8, "end": 14, "labels": ["COMPENSATION_BENEFITS"]}]
    result = _align(source, source, 0, len(source), segments)
    assert result["status"] == "UNCHANGED_MIXED_OR_UNLABELED_UNIT_REQUIRES_REVIEW"
    assert result["suggested_labels"] == []
    assert len(result["overlapping_d1_refs"]) == 2


def test_classification_unit_is_located_by_source_text_not_m1_granularity():
    text = "Đầu\n  việc khác."
    rows = [{"clause_id": "A", "clause_text": "việc  khác.", "offset_quality": "EXACT"}]
    anchors, _ = classification_text_anchors(text, rows, {"A": ["JOB_INFO"]})
    assert len(anchors) == 1
    assert text[anchors[0]["start"]:anchors[0]["end"]] == "việc khác."


def test_context_or_repeated_classification_text_never_gets_an_exact_anchor():
    rows = [{"clause_id": "A", "clause_text": "same", "offset_quality": "EXACT"},
            {"clause_id": "B", "clause_text": "unique", "offset_quality": "CONTEXT"}]
    anchors, reasons = classification_text_anchors("same same unique", rows, {"A": ["JOB_INFO"], "B": ["OTHER"]})
    assert anchors == []
    assert reasons["CONTEXT_OR_NON_EXACT_EXCLUDED"] == 1
    assert reasons["NON_UNIQUE_SOURCE_TEXT"] == 1


@pytest.mark.parametrize("mutation", [
    lambda g: g["segments"].append({"gold_clause_ref": "A", "start_char": 2, "end_char": 4, "offset_unit": "unicode_code_point"}),
    lambda g: g["segments"][0].update(end_char=99),
    lambda g: g.update(source_sha256="0"*64),
])
def test_changed_or_duplicate_source_geometry_is_rejected(mutation):
    raw = b"abcd"
    gold = {"source_sha256": hashlib.sha256(raw).hexdigest(), "segments": [
        {"gold_clause_ref": "A", "start_char": 0, "end_char": 2, "offset_unit": "unicode_code_point"},
    ]}
    mutation(gold)
    with pytest.raises(ValueError):
        checked_geometry(raw, gold)
