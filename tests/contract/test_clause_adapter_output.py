"""Đầu ra `classify_clauses().to_dict()` phải qua `clause_output_v3.json` (cần jsonschema — có ở CI)."""

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

jsonschema = pytest.importorskip("jsonschema")

from app.ai.clause_adapter import ClauseMasked, classify_clauses  # noqa: E402
from app.ai.provider import InMemoryLedger, LLMResponse  # noqa: E402

SCHEMA = json.loads((Path(__file__).resolve().parents[2] / "ai_pipeline/schemas/clause_output_v3.json").read_text("utf-8"))  # noqa: E501


class P:
    async def generate_structured(self, *, model_id, messages, response_schema, timeout_s):
        req = json.loads(messages[1]["content"])
        return LLMResponse({"items": [{"clause_id": i["clause_id"], "clause_labels": ["JOB_INFO", "LEAVE"]}
                                      for i in req["items"]]}, model_id)


def test_adapter_output_validates_against_clause_output_v3():
    cfg = SimpleNamespace(GEMINI_MODEL_ID="m", CLAUSE_BATCH_SIZE=3, LLM_PARALLELISM=2, LLM_TIMEOUT_SECONDS=5, LLM_AUTO_RETRY=1)  # noqa: E501
    out = asyncio.run(classify_clauses([ClauseMasked(f"cl_{i:04d}", "x") for i in range(1, 8)], P(), InMemoryLedger(), cfg))  # noqa: E501
    jsonschema.validate(out.to_dict(), SCHEMA)


def test_model_facing_schema_is_consistent_with_output_schema():
    from app.ai.prompts.clause_v1 import RESPONSE_SCHEMA

    item_out = SCHEMA["properties"]["items"]["items"]
    item_in = RESPONSE_SCHEMA["properties"]["items"]["items"]
    assert item_out["required"] == item_in["required"]
    assert set(item_out["properties"]) == set(item_in["properties"])
    assert SCHEMA["$defs"]["clause_label"]["enum"] == item_in["properties"]["clause_labels"]["items"]["enum"]
