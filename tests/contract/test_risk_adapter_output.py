"""Đầu ra `analyze_risks().to_dict()` phải qua `risk_output_v2.json`; schema gửi provider là tập con hợp lệ."""

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

jsonschema = pytest.importorskip("jsonschema")

from app.ai.prompts.risk_v1 import RESPONSE_SCHEMA  # noqa: E402
from app.ai.provider import InMemoryLedger, LLMResponse  # noqa: E402
from app.ai.risk_adapter import LegalCandidate, RiskItemIn, analyze_risks  # noqa: E402

SCHEMA = json.loads((Path(__file__).resolve().parents[2] / "ai_pipeline/schemas/risk_output_v2.json").read_text("utf-8"))  # noqa: E501
CFG = SimpleNamespace(GEMINI_MODEL_ID="m", RISK_BATCH_SIZE=6, LLM_PARALLELISM=2, LLM_TIMEOUT_SECONDS=5, LLM_AUTO_RETRY=1)  # noqa: E501

ITEMS = [
    {"clause_id": "cl_0001", "basis_type": "LEGAL_VIOLATION", "risk_labels": ["PROBATION", "WAGE_AMOUNT_COMPONENTS"],
     "citation_ids": ["BLLD2019:art26"], "evidence_status": "SUPPORTED",
     "explanation": "Thời gian thử việc vượt mức luật cho phép đối với người lao động."},
    {"clause_id": "cl_0002", "basis_type": "AMBIGUOUS", "risk_labels": ["PAYMENT_TIMING_METHOD"],
     "citation_ids": [], "evidence_status": "INSUFFICIENT_EVIDENCE",
     "explanation": "Kỳ hạn trả lương chưa nêu rõ nên có thể gây tranh chấp."},
]


class P:
    async def generate_structured(self, *, model_id, messages, response_schema, timeout_s):
        return LLMResponse({"schema_version": "risk_output_v2", "items": ITEMS}, model_id)


def test_adapter_output_validates_against_risk_output_v2():
    items = [
        RiskItemIn("cl_0001", "x", ["PROBATION"], ["BLLD2019:art26"]),
        RiskItemIn("cl_0002", "y", ["WAGE"] , []),
    ]
    cands = {"BLLD2019:art26": LegalCandidate("BLLD2019:art26", "nội dung")}
    out = asyncio.run(analyze_risks("EMPLOYEE", items, cands, P(), InMemoryLedger(), CFG))
    jsonschema.validate(out.to_dict(), SCHEMA)


def test_provider_schema_accepts_valid_output_and_is_subset_of_contract():
    jsonschema.Draft202012Validator.check_schema(RESPONSE_SCHEMA)
    jsonschema.validate({"schema_version": "risk_output_v2", "items": ITEMS}, RESPONSE_SCHEMA)
    jsonschema.validate({"schema_version": "risk_output_v2", "items": ITEMS}, SCHEMA)
    bad = {"schema_version": "risk_output_v2", "items": [{**ITEMS[0], "severity": "HIGH"}]}
    for s in (RESPONSE_SCHEMA, SCHEMA):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, s)
