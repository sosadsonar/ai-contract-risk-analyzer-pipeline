"""C-01 (b) khung: classify_clauses với provider mock — INV-04, INV-05, batch, song song, cancel."""

import asyncio
from types import SimpleNamespace

import pytest
from app.ai.clause_adapter import (
    ClauseMasked,
    classify_clauses,
    make_batches,
    validate_batch_response,
)
from app.ai.provider import InMemoryLedger, LLMResponse, ProviderFailure
from app.domain.errors import AiOutputInvalid, AiProviderError, StageCancelled

CFG = SimpleNamespace(GEMINI_MODEL_ID="m-1", CLAUSE_BATCH_SIZE=2, LLM_PARALLELISM=2,
                      LLM_TIMEOUT_SECONDS=30, LLM_AUTO_RETRY=1)


def items(n):
    return [ClauseMasked(f"cl_{i + 1:04d}", f"nội dung {i + 1}") for i in range(n)]


class Echo:
    """Provider giả: đọc request JSON rồi trả nhãn hợp lệ cho đúng các clause_id đã nhận."""

    def __init__(self, label="OTHER", mutate=None, delay=0.0):
        self.label, self.mutate, self.delay = label, mutate, delay
        self.requests, self.inflight, self.peak = [], 0, 0

    async def generate_structured(self, *, model_id, messages, response_schema, timeout_s):
        import json
        self.requests.append(messages)
        self.inflight += 1
        self.peak = max(self.peak, self.inflight)
        try:
            await asyncio.sleep(self.delay)
        finally:
            self.inflight -= 1
        req = json.loads(messages[1]["content"])  # [0]=system, [1]=request, [2]=feedback (retry)
        data = {"items": [{"clause_id": i["clause_id"], "clause_labels": [self.label]} for i in req["items"]]}
        if self.mutate:
            data = self.mutate(data, len(self.requests))
        return LLMResponse(data=data, model_id="m-1-resolved", in_tokens=3, out_tokens=2)


def run(n, provider, ledger=None, cfg=CFG, **kw):
    return asyncio.run(classify_clauses(items(n), provider, ledger or InMemoryLedger(), cfg, **kw))


def test_make_batches():
    assert make_batches(list(range(5)), 2) == [[0, 1], [2, 3], [4]]
    with pytest.raises(ValueError):
        make_batches([1], 0)


def test_happy_path_multi_batch_keeps_input_order_and_pins():
    p, ledger = Echo("LEAVE"), InMemoryLedger()
    out = run(5, p, ledger)
    assert [i.clause_id for i in out.items] == [f"cl_{k:04d}" for k in range(1, 6)]
    assert all(i.clause_labels == ["LEAVE"] for i in out.items)
    assert ledger.calls == 3 and out.model_id == "m-1-resolved"
    assert out.taxonomy_version == "clause_taxonomy_v03" and out.prompt_version.startswith("clause_prompt_v1+")
    d = out.to_dict()
    assert set(d) == {"schema_version", "items", "model_id", "prompt_version", "taxonomy_version"}
    assert d["schema_version"] == "clause_output_v3"


def test_parallelism_is_capped():
    p = Echo(delay=0.02)
    run(10, p, cfg=SimpleNamespace(**{**vars(CFG), "LLM_PARALLELISM": 2}))
    assert p.peak == 2


def test_inv04_outbound_payload_has_only_ids_and_masked_text():
    p = Echo()
    run(3, p)
    for msgs in p.requests:
        blob = " ".join(m["content"] for m in msgs)
        for forbidden in ("start_char", "end_char", "original_text", "structure", '"role"', "canonical"):
            assert forbidden not in blob
        assert "EMPLOYEE\"" not in msgs[1]["content"] and "EMPLOYER\"" not in msgs[1]["content"]


@pytest.mark.parametrize("extra_root", [{"confidence": 0.9}, {"model_id": "fake"}, {"taxonomy_version": "x"}])
def test_inv05_extra_root_field_rejected_even_after_retry(extra_root):
    p = Echo(mutate=lambda d, n: {**d, **extra_root})
    with pytest.raises(AiOutputInvalid):
        run(2, p)
    assert len(p.requests) == 2  # 1 lần gốc + đúng 1 retry


@pytest.mark.parametrize("field,value", [
    ("confidence", 0.9), ("type_scores", {"LEAVE": 1}), ("quote", "x"), ("span", [0, 3]),
    ("start_char", 0), ("tier", 1), ("review_zone", "GREEN"),
])
def test_inv05_extra_item_field_rejected(field, value):
    def mutate(d, n):
        d["items"][0][field] = value
        return d

    with pytest.raises(AiOutputInvalid):
        run(2, Echo(mutate=mutate))


def test_invalid_first_response_is_repaired_by_single_retry():
    def mutate(d, n):
        if n == 1:
            d["items"].pop()  # thiếu 1 id ở lần đầu
        return d

    p, ledger = Echo(mutate=mutate), InMemoryLedger()
    out = run(2, p, ledger, cfg=SimpleNamespace(**{**vars(CFG), "CLAUSE_BATCH_SIZE": 2}))
    assert len(out.items) == 2 and ledger.calls == 2
    assert "thiếu clause_id" in p.requests[1][-1]["content"]  # feedback không chứa nội dung clause
    assert "nội dung" not in p.requests[1][-1]["content"]


@pytest.mark.parametrize("bad", [
    {"items": [{"clause_id": "cl_0001", "clause_labels": ["OTHER"]}]},                                  # thiếu cl_0002
    {"items": [{"clause_id": "cl_0001", "clause_labels": ["OTHER"]}] * 2},                              # trùng
    {"items": [{"clause_id": "cl_0001", "clause_labels": ["OTHER"]},
               {"clause_id": "cl_0009", "clause_labels": ["OTHER"]}]},                                  # ID lạ
    {"items": [{"clause_id": "cl_0001", "clause_labels": ["NOPE"]},
               {"clause_id": "cl_0002", "clause_labels": ["OTHER"]}]},                                  # nhãn lạ
    {"items": [{"clause_id": "cl_0001", "clause_labels": []},
               {"clause_id": "cl_0002", "clause_labels": ["OTHER"]}]},                                  # 0 nhãn
    {"items": [{"clause_id": "cl_0001", "clause_labels": ["OTHER", "LEAVE", "TRAINING", "JOB_INFO"]},
               {"clause_id": "cl_0002", "clause_labels": ["OTHER"]}]},                                  # 4 nhãn
    {"items": [{"clause_id": "cl_0001", "clause_labels": ["LEAVE", "LEAVE"]},
               {"clause_id": "cl_0002", "clause_labels": ["OTHER"]}]},                                  # nhãn trùng
    {"items": [{"clause_id": "cl_0001", "clause_labels": "OTHER"},
               {"clause_id": "cl_0002", "clause_labels": ["OTHER"]}]},                                  # không phải list  # noqa: E501
    {"items": "x"}, {}, [],
])
def test_validate_batch_response_rejects(bad):
    with pytest.raises(ValueError):
        validate_batch_response(bad, ["cl_0001", "cl_0002"])


def test_multi_label_first_label_is_primary_and_kept_in_order():
    ok = {"items": [{"clause_id": "cl_0001", "clause_labels": ["TERMINATION", "EMPLOYER_RIGHTS_OBLIGATIONS"]}]}
    assert validate_batch_response(ok, ["cl_0001"]) == {"cl_0001": ["TERMINATION", "EMPLOYER_RIGHTS_OBLIGATIONS"]}


def test_cancel_checked_before_each_batch():
    calls = {"n": 0}

    def cancel():
        calls["n"] += 1
        return calls["n"] >= 2  # batch đầu chạy, batch hai bị hủy

    p = Echo()
    with pytest.raises(StageCancelled):
        run(6, p, cfg=SimpleNamespace(**{**vars(CFG), "LLM_PARALLELISM": 1}), cancel=cancel)
    assert len(p.requests) == 1


def test_one_failed_batch_cancels_the_rest_and_surfaces_ai_error():
    class Boom(Echo):
        async def generate_structured(self, **kw):
            if len(self.requests) == 0:
                self.requests.append(1)
                raise ProviderFailure("http", status=401)
            return await super().generate_structured(**kw)

    p = Boom(delay=0.05)
    with pytest.raises(AiProviderError) as ei:
        run(8, p)
    assert ei.value.status == 401


def test_quota_exhausted_stops_before_sending():
    p, ledger = Echo(), InMemoryLedger(max_calls=0)
    with pytest.raises(AiProviderError):
        run(2, p, ledger)
    assert p.requests == []


def test_missing_model_id_and_empty_input_and_duplicate_ids():
    with pytest.raises(ValueError):
        run(1, Echo(), cfg=SimpleNamespace(**{**vars(CFG), "GEMINI_MODEL_ID": None}))
    with pytest.raises(ValueError):
        run(0, Echo())
    dup = [ClauseMasked("cl_0001", "a"), ClauseMasked("cl_0001", "b")]
    with pytest.raises(ValueError):
        asyncio.run(classify_clauses(dup, Echo(), InMemoryLedger(), CFG))
