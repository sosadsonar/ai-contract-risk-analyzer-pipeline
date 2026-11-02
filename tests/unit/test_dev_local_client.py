"""DevLocalClient (Ollama) chạy OFFLINE bằng transport giả: định dạng request, lỗi, và cả hai adapter."""

import asyncio
import json
from types import SimpleNamespace

import pytest
from app.ai.clause_adapter import ClauseMasked, classify_clauses
from app.ai.dev_local_client import DevLocalClient
from app.ai.factory import make_provider
from app.ai.provider import InMemoryLedger, ProviderFailure
from app.ai.risk_adapter import LegalCandidate, RiskItemIn, analyze_risks
from app.clause.taxonomy import CLAUSE_LABELS
from app.domain.errors import AiOutputInvalid, AiProviderError, AiTimeout

CFG = SimpleNamespace(
    APP_ENV="dev", DEV_LLM_PROVIDER="local", TEMPERATURE=0.0, GEMINI_MODEL_ID="qwen-test", CLAUSE_BATCH_SIZE=20,
    RISK_BATCH_SIZE=6, LLM_PARALLELISM=2, LLM_TIMEOUT_SECONDS=5, LLM_AUTO_RETRY=1,
)


class FakeOllama:
    """Trả lời theo nội dung request như Ollama /api/chat với structured output."""

    def __init__(self, mode="ok"):
        self.mode, self.requests = mode, []

    def __call__(self, url, body, timeout):
        self.requests.append((url, body, timeout))
        if self.mode == "http500":
            return 500, None
        if self.mode == "timeout":
            raise ProviderFailure("timeout")
        if self.mode == "badjson":
            return 200, {"message": {"content": "không phải json"}}
        req = json.loads(body["messages"][1]["content"])
        if "role" in req:  # risk request
            data = {"schema_version": "risk_output_v2", "items": [
                {"clause_id": i["clause_id"], "basis_type": "UNFAVORABLE", "risk_labels": ["PROBATION"],
                 "citation_ids": [], "evidence_status": "INSUFFICIENT_EVIDENCE",
                 "explanation": "Điều khoản gây bất bình đẳng cho người lao động."} for i in req["items"]]}
        else:
            data = {"items": [{"clause_id": i["clause_id"], "clause_labels": [CLAUSE_LABELS[0]]} for i in req["items"]]}
        return 200, {"message": {"content": json.dumps(data)}, "prompt_eval_count": 11, "eval_count": 4}


def client(mode="ok"):
    c = DevLocalClient(app_env="dev", transport=FakeOllama(mode))
    return c, c._transport


def run(coro):
    return asyncio.run(coro)


def test_refuses_outside_dev():
    for env in ("demo", "eval"):
        with pytest.raises(ValueError):
            DevLocalClient(app_env=env)


def test_factory_selects_local_in_dev_only():
    assert isinstance(make_provider(CFG), DevLocalClient)


def test_request_body_matches_ollama_chat_contract():
    c, t = client()
    schema = {"type": "object"}
    r = run(c.generate_structured(model_id="qwen", messages=[{"role": "system", "content": "s"},
            {"role": "user", "content": json.dumps({"items": []})}], response_schema=schema, timeout_s=7))
    url, body, timeout = t.requests[0]
    assert url.endswith("/api/chat") and body["model"] == "qwen" and body["stream"] is False
    assert body["format"] == schema and body["options"] == {"temperature": 0.0} and timeout == 7.0
    assert (r.in_tokens, r.out_tokens, r.cost) == (0, 0, 0.0) or r.model_id == "qwen"


@pytest.mark.parametrize("mode, kind", [("http500", "http"), ("timeout", "timeout"), ("badjson", "invalid_json")])
def test_transport_errors_map_to_provider_failure(mode, kind):
    c, _ = client(mode)
    with pytest.raises(ProviderFailure) as e:
        run(c.generate_structured(model_id="m", messages=[{}, {"content": "{}"}], response_schema={}, timeout_s=1))
    assert e.value.kind == kind


def test_clause_classification_through_local_client():
    c, t = client()
    out = run(classify_clauses([ClauseMasked("cl_0001", "Điều 1. a"), ClauseMasked("cl_0002", "Điều 2. b")],
                               c, InMemoryLedger(), CFG))
    assert [i.clause_id for i in out.items] == ["cl_0001", "cl_0002"] and len(t.requests) == 1
    assert out.model_id == "qwen-test"


def test_risk_analysis_through_local_client_ledger_counts_tokens():
    c, t = client()
    led = InMemoryLedger()
    out = run(analyze_risks("EMPLOYEE", [RiskItemIn("cl_0001", "x", ["PROBATION"], [])],
                            {"A:art1": LegalCandidate("A:art1", "luật")}, c, led, CFG))
    assert out.items[0].evidence_status == "INSUFFICIENT_EVIDENCE" and led.in_tokens == 11 and led.out_tokens == 4


@pytest.mark.parametrize("mode, exc", [("timeout", AiTimeout), ("http500", AiProviderError), ("badjson", AiProviderError)])  # noqa: E501
def test_provider_failures_surface_as_domain_errors(mode, exc):
    c, _ = client(mode)
    with pytest.raises((exc, AiOutputInvalid)):
        run(classify_clauses([ClauseMasked("cl_0001", "Điều 1. a")], c, InMemoryLedger(), CFG))
