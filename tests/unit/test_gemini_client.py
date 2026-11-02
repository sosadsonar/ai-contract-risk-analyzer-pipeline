"""C-07: GeminiProductClient — key qua header, responseSchema, không lộ key/body (TDD §13.4)."""

import asyncio
import json

import pytest
from app.ai.clause_adapter import RESPONSE_SCHEMA  # noqa: F401  (re-export kiểm tra import)
from app.ai.gemini_client import (
    GeminiProductClient,
    parse_gemini_response,
    to_gemini_request,
    to_gemini_schema,
)
from app.ai.prompts.clause_v1 import RESPONSE_SCHEMA as CLAUSE_SCHEMA
from app.ai.provider import ProviderFailure

KEY = "AIzaSy-SECRET-KEY-123"


def ok_payload(obj, finish="STOP"):
    return {
        "candidates": [{"content": {"parts": [{"text": json.dumps(obj)}]}, "finishReason": finish}],
        "usageMetadata": {"promptTokenCount": 11, "candidatesTokenCount": 4},
        "modelVersion": "gemini-x-001",
    }


def make(transport):
    return GeminiProductClient(KEY, transport=transport)


def call(client, **kw):
    args = dict(model_id="gemini-x", messages=[{"role": "system", "content": "S"}, {"role": "user", "content": "U"}],
                response_schema={"type": "object"}, timeout_s=5)
    args.update(kw)
    return asyncio.run(client.generate_structured(**args))


def test_key_goes_in_header_never_in_url_or_body():
    seen = {}

    def transport(url, headers, body, timeout):
        seen.update(url=url, headers=headers, body=body, timeout=timeout)
        return 200, ok_payload({"items": []})

    resp = call(make(transport))
    assert "key=" not in seen["url"] and KEY not in seen["url"]
    assert seen["headers"]["x-goog-api-key"] == KEY
    assert KEY not in json.dumps(seen["body"])
    assert seen["url"].endswith("/models/gemini-x:generateContent")
    assert resp.in_tokens == 11 and resp.out_tokens == 4 and resp.model_id == "gemini-x-001"


def test_request_has_system_instruction_schema_and_temperature_zero():
    body = to_gemini_request(
        [{"role": "system", "content": "S"}, {"role": "user", "content": "U"}, {"role": "assistant", "content": "A"}],
        {"type": "object"}, temperature=0.0,
    )
    assert body["systemInstruction"] == {"parts": [{"text": "S"}]}
    assert [c["role"] for c in body["contents"]] == ["user", "model"]
    g = body["generationConfig"]
    assert g["temperature"] == 0.0 and g["responseMimeType"] == "application/json"
    assert g["responseSchema"] == {"type": "OBJECT"}


def test_schema_conversion_inlines_refs_and_drops_unsupported_keywords():
    s = {
        "$schema": "x", "$id": "y", "title": "t", "type": "object", "additionalProperties": False,
        "properties": {
            "title": {"type": "string"},  # tên property trùng từ khóa vẫn phải giữ
            "k": {"const": "clause_output_v3"},
            "l": {"type": "array", "uniqueItems": True, "minItems": 1, "items": {"$ref": "#/$defs/lab"}},
        },
        "$defs": {"lab": {"enum": ["A", "B"]}},
    }
    out = to_gemini_schema(s)
    flat = json.dumps(out)
    for bad in ("$ref", "$defs", "$schema", "additionalProperties", "uniqueItems", "const"):
        assert bad not in flat
    assert out["type"] == "OBJECT" and "title" in out["properties"]
    assert out["properties"]["k"] == {"enum": ["clause_output_v3"]}
    assert out["properties"]["l"]["items"] == {"enum": ["A", "B"]} and out["properties"]["l"]["minItems"] == 1


def test_clause_schema_converts_and_keeps_label_enum():
    out = to_gemini_schema(CLAUSE_SCHEMA)
    labels = out["properties"]["items"]["items"]["properties"]["clause_labels"]["items"]["enum"]
    assert len(labels) == 12 and "OTHER" in labels


@pytest.mark.parametrize("status", [400, 401, 403, 429, 500])
def test_http_error_becomes_failure_without_body(status):
    def transport(url, headers, body, timeout):
        return status, {"error": {"message": "NỘI DUNG PROMPT " + KEY}}

    with pytest.raises(ProviderFailure) as ei:
        call(make(transport))
    assert ei.value.kind == "http" and ei.value.status == status
    assert KEY not in str(ei.value) and "PROMPT" not in str(ei.value) and "PROMPT" not in ei.value.detail


def test_transport_timeout_and_wall_clock_timeout():
    def slow(url, headers, body, timeout):
        import time
        time.sleep(1.5)
        return 200, ok_payload({})

    with pytest.raises(ProviderFailure) as ei:
        asyncio.run(make(slow).generate_structured(
            model_id="m", messages=[{"role": "user", "content": "u"}], response_schema={"type": "object"},
            timeout_s=-1))  # wait_for(timeout=1) < 1.5s ⇒ hết giờ tổng, dù transport không tự timeout
    assert ei.value.kind == "timeout"


@pytest.mark.parametrize("finish", ["SAFETY", "MAX_TOKENS", "RECITATION"])
def test_non_stop_finish_reason_is_invalid_output(finish):
    with pytest.raises(ProviderFailure) as ei:
        parse_gemini_response(ok_payload({"a": 1}, finish=finish), "m")
    assert ei.value.kind == "invalid_json"


@pytest.mark.parametrize("payload", [{}, {"candidates": []}, {"candidates": [{"content": {"parts": [{"text": "not json"}]}}]},  # noqa: E501
                                     {"candidates": [{"content": {"parts": [{"text": "[1,2]"}]}}]}])
def test_malformed_payload_is_invalid_json(payload):
    with pytest.raises(ProviderFailure) as ei:
        parse_gemini_response(payload, "m")
    assert ei.value.kind == "invalid_json"


def test_requires_key_and_model_and_hides_key_in_repr():
    with pytest.raises(ValueError):
        GeminiProductClient(None)
    with pytest.raises(ValueError):
        call(make(lambda *a: (200, {})), model_id="")
    assert KEY not in repr(make(lambda *a: (200, {})))
