"""Scope controls report unrelated-query promotion without approving any law."""

import pytest

from scripts.prepare_wp2_scope_candidate import DELEGATED, revised_mappings, scope_exposure


def test_revised_mapping_does_not_silently_overwrite_an_existing_salary_link():
    with pytest.raises(ValueError, match="overwrite"):
        revised_mappings({"CONTRACT_TERM": {"BLLD2019:art26": 1.0},
                          "COMPENSATION_BENEFITS": {"BLLD2019:art26": 0.5}})


@pytest.mark.parametrize("old,new,expected", [(None, 4, True), (6, 5, True), (3, 1, True),
                                              (2, 2, False), (1, 2, False), (8, 7, False)])
def test_negative_scope_exposure_is_attributed_to_new_top5_or_top3_promotion(old, new, expected):
    assert scope_exposure(old, new) is expected


def test_delegated_rules_are_held_without_mutating_the_input_inventory():
    source = {"CONTRACT_TERM": {"BLLD2019:art26": 1.0}, "LEAVE": {cid: 1.0 for cid in DELEGATED}}
    revised = revised_mappings(source)
    assert revised["COMPENSATION_BENEFITS"] == {"BLLD2019:art26": 1.0}
    assert not revised["LEAVE"]
    assert len(source["LEAVE"]) == 7


def test_scope_hold_applies_to_label_citation_pair_not_every_label_for_the_law():
    from scripts.prepare_wp2_scope_candidate import recommended_review_rows

    rows = [{"label": label, "citation_id": f"BLLD2019:art29:cl{i}"}
            for label in ["JOB_INFO", "EMPLOYER_RIGHTS_OBLIGATIONS"] for i in range(1, 5)]
    result = recommended_review_rows(rows)
    assert len(result) == 4
    assert {row["label"] for row in result} == {"JOB_INFO"}
    assert len(rows) == 8
