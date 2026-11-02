"""final_result_v1 API contract: all clauses, risk subset, DEC-20 taxonomy parity."""

import copy
import json
from pathlib import Path

import pytest
from app.clause.taxonomy import CLAUSE_LABELS, DATA_TAXONOMY_VERSION
from app.core.enums import BasisType, EvidenceStatus, Role, SessionStatus, Severity
from app.risk.taxonomy import (
    RISK_LABELS,
    RISK_TAXONOMY_VERSION,
    SEVERITY_RUBRIC_VERSION,
    severity_for_labels,
)
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads(
    (ROOT / "ai_pipeline" / "schemas" / "final_result_v1.json").read_text(encoding="utf-8")
)
FIXTURE = json.loads(
    (ROOT / "tests" / "fixtures" / "mock_final_result_v1.json").read_text(encoding="utf-8")
)
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def _errors(payload):
    return list(VALIDATOR.iter_errors(payload))


def test_fixture_validates_against_final_result_schema():
    Draft202012Validator.check_schema(SCHEMA)
    assert _errors(FIXTURE) == []


def test_schema_enums_match_single_sources_of_truth_dec20():
    defs = SCHEMA["$defs"]
    risk = defs["risk"]["properties"]
    assert tuple(defs["clause_label"]["enum"]) == CLAUSE_LABELS
    assert tuple(defs["risk_label"]["enum"]) == RISK_LABELS
    assert set(SCHEMA["properties"]["role"]["enum"]) == {v.value for v in Role}
    assert SCHEMA["properties"]["status"]["const"] == SessionStatus.COMPLETED.value
    assert set(defs["risk_basis"]["properties"]["basis_type"]["enum"]) == {
        v.value for v in BasisType
    }
    assert set(risk["evidence_status"]["enum"]) == {v.value for v in EvidenceStatus}
    assert set(risk["severity"]["oneOf"][0]["enum"]) == {v.value for v in Severity}
    assert risk["severity"]["oneOf"][1] == {"type": "null"}


def test_fixture_code_point_partition_includes_every_clause():
    text = FIXTURE["canonical_text"]
    assert any(ord(character) > 0xFFFF for character in text)
    assert FIXTURE["offset_unit"] == "unicode_code_point"
    clauses = FIXTURE["clauses"]
    assert len(clauses) == 2
    assert len({clause["clause_id"] for clause in clauses}) == len(clauses)
    cursor = 0
    for clause in clauses:
        start, end = clause["start_char"], clause["end_char"]
        assert start == cursor
        assert start < end <= len(text)
        assert text[start:end] == clause["original_text"]
        cursor = end
    assert cursor == len(text)


def test_fixture_risks_reference_only_risk_bearing_clauses_and_citations():
    clause_ids = {clause["clause_id"] for clause in FIXTURE["clauses"]}
    risks = FIXTURE["risks"]
    assert len(risks) == 1
    assert len({risk["clause_id"] for risk in risks}) == len(risks)
    assert {risk["clause_id"] for risk in risks} < clause_ids
    citations = {citation["citation_id"] for citation in FIXTURE["citations"]}
    assert len(citations) == len(FIXTURE["citations"])
    for risk in risks:
        assert risk["evidence_status"] == EvidenceStatus.SUPPORTED.value
        assert risk["citation_ids"]
        assert set(risk["citation_ids"]) <= citations
        assert [entry["label"] for entry in risk["risk_basis"]] == risk["risk_labels"]
        assert len({entry["label"] for entry in risk["risk_basis"]}) == len(risk["risk_basis"])
        for basis in risk["risk_basis"]:
            assert severity_for_labels(
                [basis["label"]], basis["basis_type"], FIXTURE["role"]
            ) is not None
        expected = max(
            (severity_for_labels([basis["label"]], basis["basis_type"], FIXTURE["role"])
             for basis in risk["risk_basis"]),
            key={Severity.LOW: 1, Severity.MEDIUM: 2, Severity.HIGH: 3}.__getitem__,
        )
        assert risk["severity"] == expected.value
    assert FIXTURE["version_pins"]["clause_taxonomy_version"] == DATA_TAXONOMY_VERSION
    assert FIXTURE["version_pins"]["risk_taxonomy_version"] == RISK_TAXONOMY_VERSION
    assert FIXTURE["version_pins"]["severity_rubric_version"] == SEVERITY_RUBRIC_VERSION


@pytest.mark.parametrize("field", SCHEMA["required"])
def test_missing_required_result_field_is_rejected(field):
    payload = copy.deepcopy(FIXTURE)
    del payload[field]
    assert _errors(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("offset_unit", "utf16_code_unit"),
        ("role", "ADMIN"),
        ("status", "PROCESSING"),
        ("session_id", "not-a-uuid"),
        ("analysis_date", "not-a-date"),
    ],
)
def test_invalid_metadata_is_rejected(field, value):
    payload = copy.deepcopy(FIXTURE)
    payload[field] = value
    assert _errors(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("evidence_status", "UNKNOWN"),
        ("risk_labels", ["NOT_IN_TAXONOMY"]),
        ("severity", "CRITICAL"),
        ("citation_ids", []),
    ],
)
def test_invalid_supported_risk_is_rejected(field, value):
    payload = copy.deepcopy(FIXTURE)
    payload["risks"][0][field] = value
    assert _errors(payload)


def test_insufficient_evidence_has_no_severity_or_citation():
    payload = copy.deepcopy(FIXTURE)
    risk = payload["risks"][0]
    risk.update(evidence_status="INSUFFICIENT_EVIDENCE", severity=None, citation_ids=[])
    assert _errors(payload) == []
    risk["severity"] = "HIGH"
    assert _errors(payload)
