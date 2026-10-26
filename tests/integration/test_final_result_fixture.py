"""Offline end-to-end assertions for the mock final-result contract.

The old pipeline script used fabricated spans that did not match its text. These
checks use the same fixture served by the mock API instead of running a provider.
"""

import json
from pathlib import Path

from app.clause.taxonomy import validate_labels
from app.core.enums import EvidenceStatus
from app.risk.taxonomy import severity_for
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "mock_final_result_v1.json"
SCHEMA = ROOT / "ai_pipeline" / "schemas" / "final_result_v1.json"


def test_mock_result_conforms_to_final_schema():
    result = json.loads(FIXTURE.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert list(Draft202012Validator(schema).iter_errors(result)) == []


def test_all_clauses_partition_canonical_text_at_code_point_offsets():
    result = json.loads(FIXTURE.read_text(encoding="utf-8"))
    text = result["canonical_text"]
    assert any(ord(character) > 0xFFFF for character in text)
    cursor = 0
    ids = set()
    for clause in result["clauses"]:
        assert clause["start_char"] == cursor
        cursor = clause["end_char"]
        assert text[clause["start_char"] : cursor] == clause["original_text"]
        assert clause["clause_id"] not in ids
        ids.add(clause["clause_id"])
        assert validate_labels(clause["clause_labels"]) == clause["clause_labels"]
    assert cursor == len(text)
    assert result["offset_unit"] == "unicode_code_point"


def test_risks_only_reference_partitioned_clauses_and_citations():
    result = json.loads(FIXTURE.read_text(encoding="utf-8"))
    clause_ids = {clause["clause_id"] for clause in result["clauses"]}
    citation_ids = {citation["citation_id"] for citation in result["citations"]}
    risk_ids = [risk["clause_id"] for risk in result["risks"]]
    assert risk_ids and len(risk_ids) == len(set(risk_ids))
    assert set(risk_ids) < clause_ids  # The ordinary clause must remain in clauses.
    for risk in result["risks"]:
        assert risk["risk_labels"]
        assert {item["label"] for item in risk["risk_basis"]} == set(risk["risk_labels"])
        assert set(risk["citation_ids"]) <= citation_ids
        if risk["evidence_status"] == EvidenceStatus.SUPPORTED:
            assert risk["citation_ids"]
            expected = [
                severity_for(item["label"], item["basis_type"], result["role"])
                for item in risk["risk_basis"]
            ]
            assert all(expected)
            assert risk["severity"] == max(expected, key={"LOW": 1, "MEDIUM": 2, "HIGH": 3}.get)
