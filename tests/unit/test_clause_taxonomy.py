"""C-03/C-04: taxonomy là nguồn duy nhất; validate_labels thay cho labeling.py cũ."""

import pytest
from app.clause import taxonomy
from app.clause.taxonomy import CLAUSE_LABELS, validate_labels


def test_twelve_unique_labels_and_definitions_cover_them():
    assert len(CLAUSE_LABELS) == 12
    assert len(set(CLAUSE_LABELS)) == 12
    assert set(taxonomy.LABEL_DEFINITIONS) == set(CLAUSE_LABELS)


def test_version_semantics_are_separated():
    assert taxonomy.DATA_TAXONOMY_VERSION == "clause_taxonomy_v03"
    assert taxonomy.TAXONOMY_VERSION == "v04"


def test_legacy_concepts_are_gone():
    for name in ("MultiLabelRule", "MULTI_LABEL_RULE", "resolve_multi_labels", "validate_scores",
                 "build_clause", "compute_clause_routing"):
        assert not hasattr(taxonomy, name)


@pytest.mark.parametrize(
    "labels",
    [["OTHER"], ["JOB_INFO", "LEAVE"], ["JOB_INFO", "LEAVE", "TRAINING"]],
)
def test_valid_label_sets_returned_in_order(labels):
    assert validate_labels(labels) == labels


@pytest.mark.parametrize(
    "labels,msg",
    [
        ([], "1..3"),
        (["JOB_INFO", "LEAVE", "TRAINING", "OTHER"], "1..3"),
        (["JOB_INFO", "JOB_INFO"], "trùng"),
        (["NOT_A_LABEL"], "ngoài taxonomy"),
        ("JOB_INFO", "list"),
        (None, "list"),
    ],
)
def test_invalid_label_sets_raise(labels, msg):
    with pytest.raises(ValueError, match=msg):
        validate_labels(labels)
