"""Hợp đồng clause_output_v3 (TDD §6.5, §13.2, Phụ lục A.1) + INV-05 ở mức schema."""

import copy
import json
from pathlib import Path

import pytest
from app.clause.taxonomy import DATA_TAXONOMY_VERSION
from jsonschema import Draft202012Validator

from ai_pipeline.services.mock_clause_service import get_mock_clause_output

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "ai_pipeline" / "schemas" / "clause_output_v3.json"
)

@pytest.fixture(scope="module")
def validator():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


@pytest.fixture
def payload():
    return get_mock_clause_output()


def _errors(validator, doc):
    return list(validator.iter_errors(doc))


def test_mock_output_is_valid(validator, payload):
    assert _errors(validator, payload) == []


def test_mock_uses_data_taxonomy_version_not_prompt_revision(payload):
    # TDD §6.4: taxonomy_version = version nguồn của data (v03), KHÔNG phải revision prompt v04.
    assert payload["taxonomy_version"] == DATA_TAXONOMY_VERSION == "clause_taxonomy_v03"


@pytest.mark.parametrize(
    "legacy_field", ["contract_id", "multi_label_rule_version", "total_clauses", "clauses"]
)
def test_legacy_top_level_fields_rejected(validator, payload, legacy_field):
    payload[legacy_field] = "x"
    assert _errors(validator, payload)


@pytest.mark.parametrize(
    "forbidden", ["type_scores", "max_content_risk_tier", "review_zone", "start_char", "end_char",
                  "span", "original_text", "quote", "confidence", "role"]
)
def test_inv05_llm_cannot_return_scores_span_quote_or_role(validator, payload, forbidden):
    payload["items"][0][forbidden] = 0.9
    assert _errors(validator, payload)


def test_schema_version_is_pinned(validator, payload):
    payload["schema_version"] = "2.0"
    assert _errors(validator, payload)


@pytest.mark.parametrize("bad_id", ["clause_1", "cl_1", "cl_00001", "CL_0001", ""])
def test_clause_id_format(validator, payload, bad_id):
    payload["items"][0]["clause_id"] = bad_id
    assert _errors(validator, payload)


@pytest.mark.parametrize(
    "bad_labels",
    [
        [],                                              # < 1
        ["JOB_INFO", "LEAVE", "TRAINING", "OTHER"],      # > 3
        ["JOB_INFO", "JOB_INFO"],                        # trùng
        ["CONFIDENTIALITY_IP"],                          # nhãn cũ đã bỏ
        ["job_info"],                                    # sai chữ hoa/thường
    ],
)
def test_clause_labels_constraints(validator, payload, bad_labels):
    payload["items"][0]["clause_labels"] = bad_labels
    assert _errors(validator, payload)


@pytest.mark.parametrize(
    "missing",
    ["schema_version", "items", "model_id", "prompt_version", "taxonomy_version"],
)
def test_required_fields(validator, payload, missing):
    doc = copy.deepcopy(payload)
    del doc[missing]
    assert _errors(validator, doc)
