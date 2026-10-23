"""Hợp đồng risk_output_v2: schema CHỈ cho câu trả lời LLM ở stage risk_severity_explain."""

import copy
import json
from pathlib import Path

import pytest
from app.core.enums import BasisType, EvidenceStatus
from app.risk.taxonomy import RISK_LABELS
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "ai_pipeline" / "schemas" / "risk_output_v2.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA)


def _errors(doc):
    return list(VALIDATOR.iter_errors(doc))


def _payload():
    return copy.deepcopy(SCHEMA["examples"][0])


def test_schema_is_valid_and_examples_pass():
    Draft202012Validator.check_schema(SCHEMA)
    for example in SCHEMA["examples"]:
        assert _errors(example) == []


def test_label_enum_matches_code_in_order():
    assert tuple(SCHEMA["$defs"]["risk_label"]["enum"]) == RISK_LABELS


def test_basis_and_evidence_enums_match_code():
    props = SCHEMA["$defs"]["risk_item"]["properties"]
    assert set(props["basis_type"]["enum"]) == {b.value for b in BasisType}
    assert set(props["evidence_status"]["enum"]) == {e.value for e in EvidenceStatus}


def test_severity_is_not_an_llm_field():
    assert "severity" not in SCHEMA["$defs"]["risk_item"]["properties"]
    assert "severity" not in SCHEMA["$defs"]["risk_item"]["required"]


def test_empty_items_means_no_risk_found():
    assert _errors({"schema_version": "risk_output_v2", "items": []}) == []


@pytest.mark.parametrize(
    "forbidden",
    [
        "model_id",
        "prompt_version",
        "risk_taxonomy_version",
        "severity_rubric_version",
        "role",
        "session_id",
        "severity",
    ],
)
def test_llm_cannot_return_backend_owned_top_level_fields(forbidden):
    doc = _payload()
    doc[forbidden] = "x"
    assert _errors(doc)


@pytest.mark.parametrize(
    "forbidden", ["start_char", "end_char", "span", "original_text", "quote", "role", "risk_basis"]
)
def test_llm_cannot_return_span_quote_or_role_in_items(forbidden):
    doc = _payload()
    doc["items"][0][forbidden] = 1
    assert _errors(doc)


def test_supported_requires_citation():
    doc = _payload()
    doc["items"][0]["citation_ids"] = []
    assert _errors(doc)


def test_insufficient_evidence_requires_no_citation():
    doc = _payload()
    doc["items"][1]["citation_ids"] = ["BLLD2019:art17"]
    assert _errors(doc)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda i: i.update(risk_labels=[]),
        lambda i: i.update(
            risk_labels=["PROBATION", "REST_AND_LEAVE", "SOCIAL_INSURANCE", "OSH_OBLIGATION"]
        ),
        lambda i: i.update(risk_labels=["PROBATION", "PROBATION"]),
        lambda i: i.update(risk_labels=["NOT_A_LABEL"]),
        lambda i: i.update(basis_type="UNKNOWN"),
        lambda i: i.update(clause_id="cl_1"),
        lambda i: i.update(explanation=""),
        lambda i: i.pop("explanation"),
        lambda i: i.pop("basis_type"),
    ],
)
def test_item_constraints(mutate):
    doc = _payload()
    mutate(doc["items"][0])
    assert _errors(doc)


def test_schema_version_is_pinned():
    doc = _payload()
    doc["schema_version"] = "risk_output_v1"
    assert _errors(doc)
