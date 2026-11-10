"""risk_adapter (C-15 khung): provider giả, validate chặt, batching, cancel, ghi pin."""

import asyncio
import json
from types import SimpleNamespace

import pytest
from app.ai.provider import InMemoryLedger, LLMResponse
from app.ai.risk_adapter import (
    LegalCandidate,
    RelatedClause,
    RiskItemIn,
    analyze_risks,
    make_batches,
    validate_batch_response,
)
from app.domain.errors import AiOutputInvalid, StageCancelled

CFG = SimpleNamespace(
    GEMINI_MODEL_ID="m-test", RISK_BATCH_SIZE=2, LLM_PARALLELISM=2, LLM_TIMEOUT_SECONDS=5, LLM_AUTO_RETRY=1
)
CANDS = {
    "BLLD2019:art26": LegalCandidate("BLLD2019:art26", "Thử việc tối đa...", "Bộ luật Lao động 2019", "Điều 25"),
    "BLLD2019:art35": LegalCandidate("BLLD2019:art35", "Đơn phương chấm dứt...", "Bộ luật Lao động 2019", "Điều 35"),
}


def item(n, cands=("BLLD2019:art26",), related=()):
    return RiskItemIn(f"cl_{n:04d}", f"Điều khoản số {n} <NAME>___", ["PROBATION"], list(cands), list(related))


def good(cid, **kw):
    d = {
        "clause_id": cid, "basis_type": "UNFAVORABLE", "risk_labels": ["PROBATION"],
        "citation_ids": ["BLLD2019:art26"], "evidence_status": "SUPPORTED",
        "explanation": "Điều khoản thử việc bất lợi cho người lao động.",
    }
    d.update(kw)
    return d


def resp(items):
    return {"schema_version": "risk_output_v2", "items": items}


class FakeProvider:
    def __init__(self, fn):
        self.fn, self.calls = fn, []

    async def generate_structured(self, *, model_id, messages, response_schema, timeout_s):
        self.calls.append({"model_id": model_id, "messages": messages, "schema": response_schema})
        return LLMResponse(data=self.fn(len(self.calls), messages), model_id=model_id, in_tokens=10, out_tokens=5)


def run(coro):
    return asyncio.run(coro)


def echo_all(_n, messages):
    req = json.loads(messages[1]["content"])
    return resp([good(i["clause_id"]) for i in req["items"]])


def test_make_batches():
    assert make_batches([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
    with pytest.raises(ValueError):
        make_batches([1], 0)


def test_happy_path_batches_orders_and_pins():
    p, led = FakeProvider(echo_all), InMemoryLedger()
    out = run(analyze_risks("EMPLOYEE", [item(1), item(2), item(3)], CANDS, p, led, CFG))
    assert [i.clause_id for i in out.items] == ["cl_0001", "cl_0002", "cl_0003"]
    assert len(p.calls) == 2
    assert out.model_id == "m-test" and out.prompt_version.startswith("risk_prompt_v1+")
    assert out.pins()["severity_rubric_version"] == "severity_v01"
    assert set(out.to_dict()) == {"schema_version", "items"}
    assert out.citations_outside_candidate == 0


def test_request_has_role_dedupes_catalog_and_no_original_text():
    p = FakeProvider(echo_all)
    rel = RelatedClause("cl_0009", "REFERS_TO", "Điều khoản liên quan")
    run(analyze_risks("EMPLOYER", [item(1, related=[rel]), item(2, ("BLLD2019:art26", "BLLD2019:art35"))],
                      CANDS, p, InMemoryLedger(), CFG))
    req = json.loads(p.calls[0]["messages"][1]["content"])
    assert req["role"] == "EMPLOYER"
    assert set(req["candidates"]) == {"BLLD2019:art26", "BLLD2019:art35"}
    assert req["items"][0]["related_clauses"][0]["clause_id"] == "cl_0009"
    assert "canonical" not in json.dumps(req) and p.calls[0]["schema"]["required"] == ["schema_version", "items"]


def test_clause_without_risk_may_be_omitted_and_empty_items_ok():
    p = FakeProvider(lambda n, m: resp([]))
    out = run(analyze_risks("EMPLOYEE", [item(1), item(2)], CANDS, p, InMemoryLedger(), CFG))
    assert out.items == []


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(extra=1),
        lambda d: d.update(schema_version="risk_output_v1"),
        lambda d: d["items"][0].update(severity="HIGH"),
        lambda d: d["items"][0].update(clause_id="cl_0099"),
        lambda d: d["items"].append(dict(d["items"][0])),
        lambda d: d["items"][0].update(basis_type="BAD"),
        lambda d: d["items"][0].update(risk_labels=[]),
        lambda d: d["items"][0].update(risk_labels=["PROBATION", "PROBATION"]),
        lambda d: d["items"][0].update(risk_labels=["NOT_A_LABEL"]),
        lambda d: d["items"][0].update(risk_labels=["PROBATION", "REST_AND_LEAVE", "SOCIAL_INSURANCE", "OSH_OBLIGATION"]),  # noqa: E501
        lambda d: d["items"][0].update(citation_ids=[]),
        lambda d: d["items"][0].update(evidence_status="INSUFFICIENT_EVIDENCE"),
        lambda d: d["items"][0].update(evidence_status="MAYBE"),
        lambda d: d["items"][0].update(explanation="ngắn"),
        lambda d: d["items"][0].update(citation_ids=["BLLD2019:art26", "BLLD2019:art26"]),
    ],
)
def test_validation_rejects_bad_responses(mutate):
    d = resp([good("cl_0001")])
    mutate(d)
    with pytest.raises(ValueError):
        validate_batch_response(d, [item(1)])


def test_insufficient_evidence_requires_empty_citations():
    ok = resp([good("cl_0001", evidence_status="INSUFFICIENT_EVIDENCE", citation_ids=[])])
    assert validate_batch_response(ok, [item(1)])[0].citation_ids == []


def test_invalid_output_retries_once_then_raises_with_code():
    p = FakeProvider(lambda n, m: resp([good("cl_0001", basis_type="BAD")]))
    led = InMemoryLedger()
    with pytest.raises(AiOutputInvalid) as e:
        run(analyze_risks("EMPLOYEE", [item(1)], CANDS, p, led, CFG))
    assert e.value.code == "AI_OUTPUT_INVALID" and len(p.calls) == 2
    assert "Điều khoản số" not in str(e.value)  # lỗi không chứa nội dung hợp đồng


def test_retry_recovers_after_one_bad_response():
    p = FakeProvider(lambda n, m: resp([good("cl_0001", risk_labels=["X"])]) if n == 1 else echo_all(n, m))
    out = run(analyze_risks("EMPLOYEE", [item(1)], CANDS, p, InMemoryLedger(), CFG))
    assert len(p.calls) == 2 and out.items[0].clause_id == "cl_0001"


def test_citation_outside_candidate_is_counted_not_rejected():
    p = FakeProvider(lambda n, m: resp([good("cl_0001", citation_ids=["BLLD2019:art35"])]))
    out = run(analyze_risks("EMPLOYEE", [item(1)], CANDS, p, InMemoryLedger(), CFG))
    assert out.citations_outside_candidate == 1 and out.items[0].citation_ids == ["BLLD2019:art35"]


def test_cancel_checked_before_each_batch():
    p = FakeProvider(echo_all)
    with pytest.raises(StageCancelled):
        run(analyze_risks("EMPLOYEE", [item(1), item(2), item(3)], CANDS, p, InMemoryLedger(), CFG, cancel=lambda: True))  # noqa: E501
    assert p.calls == []


@pytest.mark.parametrize(
    "role, items, err",
    [
        ("ADMIN", [item(1)], "role"),
        ("EMPLOYEE", [item(1), item(1)], "trùng"),
        ("EMPLOYEE", [item(1, ("NOPE:art1",))], "catalog"),
        ("EMPLOYEE", [], "không có clause"),
    ],
)
def test_input_validation(role, items, err):
    with pytest.raises(ValueError, match=err):
        run(analyze_risks(role, items, CANDS, FakeProvider(echo_all), InMemoryLedger(), CFG))


def test_missing_model_id_is_refused():
    cfg = SimpleNamespace(**{**CFG.__dict__, "GEMINI_MODEL_ID": None})
    with pytest.raises(ValueError, match="model"):
        run(analyze_risks("EMPLOYEE", [item(1)], CANDS, FakeProvider(echo_all), InMemoryLedger(), cfg))


def test_related_clause_ids_inside_context_are_kept():
    items = [item(1, related=[RelatedClause("cl_0002", "REFERS_TO", "x")]), item(2)]
    p = FakeProvider(lambda n, m: resp([good("cl_0001", related_clause_ids=["cl_0002"])]))
    out = run(analyze_risks("EMPLOYEE", items, CANDS, p, InMemoryLedger(), CFG))
    assert out.items[0].related_clause_ids == ["cl_0002"]
    assert out.to_dict()["items"][0]["related_clause_ids"] == ["cl_0002"]


def test_related_clause_id_outside_context_is_rejected():
    p = FakeProvider(lambda n, m: resp([good("cl_0001", related_clause_ids=["cl_0009"])]))
    with pytest.raises(AiOutputInvalid):
        run(analyze_risks("EMPLOYEE", [item(1)], CANDS, p, InMemoryLedger(), CFG))


def test_related_clause_self_reference_and_duplicates_are_rejected():
    ctx = [RelatedClause("cl_0002", "REFERS_TO", "x")]
    for bad in (["cl_0001"], ["cl_0002", "cl_0002"]):
        with pytest.raises(ValueError):
            validate_batch_response(resp([good("cl_0001", related_clause_ids=bad)]), [item(1, related=ctx)])


def test_optional_key_does_not_relax_unknown_key_check():
    with pytest.raises(ValueError):
        validate_batch_response(resp([good("cl_0001", severity="HIGH")]), [item(1)])


def test_absent_or_empty_related_clause_ids_keeps_old_output():
    out = validate_batch_response(resp([good("cl_0001")]), [item(1)])
    assert out[0].to_dict() == {
        "clause_id": "cl_0001", "basis_type": "UNFAVORABLE", "risk_labels": ["PROBATION"],
        "citation_ids": ["BLLD2019:art26"], "evidence_status": "SUPPORTED",
        "explanation": "Điều khoản thử việc bất lợi cho người lao động.",
    }
    out = validate_batch_response(resp([good("cl_0001", related_clause_ids=[])]), [item(1)])
    assert "related_clause_ids" not in out[0].to_dict()
