"""C-07/C-01 (b): prompt Clause v1 sinh từ taxonomy; request chỉ có clause_id + masked_text (INV-04)."""

import json
from unittest import mock

from app.ai.prompts import clause_v1
from app.ai.prompts.clause_v1 import (
    RESPONSE_SCHEMA,
    build_messages,
    build_request,
    build_system_prompt,
    prompt_pin,
)
from app.clause.taxonomy import CLAUSE_LABELS, DATA_TAXONOMY_VERSION, LABEL_DEFINITIONS


def test_system_prompt_lists_every_label_with_its_definition():
    p = build_system_prompt()
    for name in CLAUSE_LABELS:
        assert f"- {name}: {LABEL_DEFINITIONS[name]}" in p


def test_schema_enum_equals_taxonomy_in_order():
    enum = RESPONSE_SCHEMA["properties"]["items"]["items"]["properties"]["clause_labels"]["items"]["enum"]
    assert tuple(enum) == CLAUSE_LABELS


def test_changing_a_definition_changes_prompt_pin():
    before = prompt_pin()
    changed = dict(LABEL_DEFINITIONS, OTHER="định nghĩa khác")
    with mock.patch.object(clause_v1, "LABEL_DEFINITIONS", changed):
        assert prompt_pin() != before
    assert prompt_pin() == before


def test_request_contains_only_ids_and_masked_text_and_no_role():
    req = build_request([("cl_0001", "Điều 1. Lương <NAME>____"), ("cl_0002", "b")])
    assert set(req) == {"schema_version", "taxonomy_version", "items"}
    assert req["taxonomy_version"] == DATA_TAXONOMY_VERSION
    assert all(set(i) == {"clause_id", "masked_text"} for i in req["items"])
    msgs = build_messages([("cl_0001", "x")])
    assert [m["role"] for m in msgs] == ["system", "user"]
    assert json.loads(msgs[1]["content"])["items"] == [{"clause_id": "cl_0001", "masked_text": "x"}]
    blob = msgs[0]["content"] + msgs[1]["content"]
    assert '"role"' not in blob and "vai trò" not in blob.lower()  # không role (TDD §13.1)


def test_prompt_forbids_risk_advice_and_confidence():
    p = build_system_prompt().lower()
    assert "không đánh giá rủi ro" in p and "lời khuyên" in p
