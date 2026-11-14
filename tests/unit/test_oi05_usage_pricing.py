"""SRS OI-05 §2.4: usage của response lỗi vẫn vào ledger; cost từ bảng giá có nguồn."""

import asyncio
from types import SimpleNamespace

import pytest
from app.ai.factory import price_from
from app.ai.gemini_client import GeminiProductClient, Price, parse_gemini_response
from app.ai.provider import InMemoryLedger, ProviderFailure, call_with_retry
from app.domain.errors import AiOutputInvalid


def _payload(text, prompt=100, cand=20, thoughts=0, finish="STOP"):
    usage = {"promptTokenCount": prompt, "candidatesTokenCount": cand}
    if thoughts:
        usage["thoughtsTokenCount"] = thoughts
    return {"candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": finish}],
            "usageMetadata": usage}


def test_invalid_json_failure_carries_usage():
    with pytest.raises(ProviderFailure) as caught:
        parse_gemini_response(_payload("{not json", 100, 20), "m")
    assert (caught.value.in_tokens, caught.value.out_tokens) == (100, 20)
    with pytest.raises(ProviderFailure) as caught:
        parse_gemini_response(_payload("{}", 90, 15, finish="MAX_TOKENS"), "m")
    assert caught.value.usage_known and caught.value.out_tokens == 15


def test_missing_usage_is_unknown_not_zero():
    payload = {"candidates": [{"content": {"parts": [{"text": "{}"}]}}]}
    assert parse_gemini_response(payload, "m").usage_known is False
    with pytest.raises(ProviderFailure) as caught:
        parse_gemini_response({"candidates": []}, "m")
    assert caught.value.usage_known is False and caught.value.in_tokens is None


def test_thinking_tokens_count_as_output_and_price_applied():
    price = Price(0.30, 2.50, "https://ai.google.dev/pricing (ngày hiệu lực ghi khi cấu hình)")
    resp = parse_gemini_response(_payload("{}", 1_000_000, 100_000, thoughts=100_000), "m", price)
    assert resp.out_tokens == 200_000
    assert resp.cost == pytest.approx(0.30 + 0.5)


def test_ledger_keeps_usage_of_failed_then_retried_call():
    """Tái hiện review: transport 210/45 nhưng ledger cũ chỉ giữ 110/25."""
    payloads = iter([_payload("{bad", 100, 20), _payload("{\"ok\": 1}", 110, 25)])
    client = GeminiProductClient("k", transport=lambda *a: (200, next(payloads)))
    ledger = InMemoryLedger()
    resp, _ = asyncio.run(call_with_retry(client, ledger, model_id="m", messages=[{"role": "user", "content": "x"}],
                                          response_schema={"type": "object"}, timeout_s=5,
                                          sleep=lambda s: asyncio.sleep(0)))
    assert resp.data == {"ok": 1}
    assert (ledger.calls, ledger.in_tokens, ledger.out_tokens) == (2, 210, 45)
    assert ledger.errors == ["invalid_json"]


def test_exhausted_retry_still_records_both_usages():
    client = GeminiProductClient("k", transport=lambda *a: (200, _payload("{bad", 50, 5)))
    ledger = InMemoryLedger()
    with pytest.raises(AiOutputInvalid):
        asyncio.run(call_with_retry(client, ledger, model_id="m", messages=[{"role": "user", "content": "x"}],
                                    response_schema={"type": "object"}, timeout_s=5))
    assert (ledger.calls, ledger.in_tokens, ledger.out_tokens) == (2, 100, 10)


def test_price_requires_all_three_settings():
    assert price_from(SimpleNamespace(LLM_PRICE_INPUT_USD_PER_MTOK=0.3, LLM_PRICE_OUTPUT_USD_PER_MTOK=2.5,
                                      LLM_PRICE_SOURCE=None)) is None
    price = price_from(SimpleNamespace(LLM_PRICE_INPUT_USD_PER_MTOK=0.3, LLM_PRICE_OUTPUT_USD_PER_MTOK=2.5,
                                       LLM_PRICE_SOURCE="url 2026-11-13"))
    assert price == Price(0.3, 2.5, "url 2026-11-13")


def test_env_example_has_provisional_oi05_values():
    from pathlib import Path
    text = (Path(__file__).resolve().parents[2] / ".env.example").read_text(encoding="utf-8")
    assert "DAILY_LLM_CALL_QUOTA=300" in text and "SESSION_CALL_RESERVE=40" in text
    assert "GIÁ TRỊ TẠM" in text
