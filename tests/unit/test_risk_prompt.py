"""Prompt risk_v1: sinh từ taxonomy, request đúng hợp đồng, không rò dữ liệu (INV-04)."""

import json
from pathlib import Path

from app.ai.prompts import risk_v1 as rv
from app.core.enums import BasisType
from app.risk.taxonomy import RISK_LABELS, RISK_TAXONOMY_VERSION

SCHEMA = json.loads(
    (Path(__file__).resolve().parents[2] / "ai_pipeline" / "schemas" / "risk_output_v2.json").read_text(encoding="utf-8")  # noqa: E501
)


def test_definitions_cover_exactly_the_taxonomy_in_order():
    assert list(rv.RISK_LABEL_DEFINITIONS) == list(RISK_LABELS)
    assert all(d.strip().endswith((".", ")")) or len(d) > 20 for d in rv.RISK_LABEL_DEFINITIONS.values())


def test_definitions_do_not_cite_law_articles():
    for text in rv.RISK_LABEL_DEFINITIONS.values():
        assert "Điều " not in text and "Nghị định" not in text and "Bộ luật" not in text


def test_basis_types_match_enum():
    assert set(rv.BASIS_TYPE_DEFINITIONS) == {b.value for b in BasisType}


def test_response_schema_enums_match_contract_schema():
    item = rv.RESPONSE_SCHEMA["properties"]["items"]["items"]
    assert item["properties"]["risk_labels"]["items"]["enum"] == list(RISK_LABELS)
    assert set(item["required"]) == set(item["properties"])
    text = json.dumps(SCHEMA)
    for name in RISK_LABELS:
        assert name in text
    assert rv.OUTPUT_SCHEMA_VERSION == "risk_output_v2"


def test_system_prompt_is_role_independent_and_has_no_label_list():
    p = rv.build_system_prompt()
    assert "EMPLOYEE" in p and "EMPLOYER" in p
    assert "WAGE_AMOUNT_COMPONENTS" not in p  # nhãn nằm trong request, không trùng ở system prompt


def test_request_shape_has_no_forbidden_fields():
    req = rv.build_request("EMPLOYEE", [{"clause_id": "cl_0001", "masked_text": "x"}], {})
    assert set(req) == {"schema_version", "role", "risk_taxonomy", "basis_types", "candidates", "items"}
    assert req["schema_version"] == "risk_analysis_request_v2"
    assert [t["label"] for t in req["risk_taxonomy"]] == list(RISK_LABELS)
    dumped = json.dumps(req)
    for banned in ("canonical_text", "original", "start", "end", "severity"):
        assert f'"{banned}"' not in dumped


def test_messages_and_pin():
    msgs = rv.build_messages(rv.build_request("EMPLOYER", [], {}))
    assert [m["role"] for m in msgs] == ["system", "user"]
    assert json.loads(msgs[1]["content"])["role"] == "EMPLOYER"
    assert rv.prompt_pin().startswith(f"{rv.RISK_PROMPT_VERSION}+{RISK_TAXONOMY_VERSION}+")
    assert rv.prompt_pin() == rv.prompt_pin()
