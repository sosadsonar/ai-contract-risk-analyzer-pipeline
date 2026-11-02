"""C-07: call_with_retry — retry matrix TDD §13.4, ledger đếm MỌI request thật (kể cả retry)."""

import asyncio

import pytest
from app.ai.provider import (
    InMemoryLedger,
    LLMResponse,
    ProviderFailure,
    call_with_retry,
)
from app.domain.errors import AiOutputInvalid, AiProviderError, AiTimeout

SCHEMA = {"type": "object"}
MSGS = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]


class Scripted:
    """Provider giả: mỗi lần gọi lấy một phần tử của script (Exception → raise, dict → trả)."""

    def __init__(self, *script):
        self.script = list(script)
        self.calls = []

    async def generate_structured(self, *, model_id, messages, response_schema, timeout_s):
        self.calls.append(messages)
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        return LLMResponse(data=step, model_id=model_id, in_tokens=10, out_tokens=5)


def run(provider, ledger=None, **kw):
    ledger = ledger or InMemoryLedger()
    sleeps = []

    async def fake_sleep(s):
        sleeps.append(s)

    out = asyncio.run(
        call_with_retry(
            provider, ledger, model_id="m", messages=MSGS, response_schema=SCHEMA, timeout_s=30,
            sleep=fake_sleep, rng=lambda: 0.5, **kw,
        )
    )
    return out, ledger, sleeps


def test_success_counts_one_call_and_tokens():
    (resp, _), ledger, _ = run(Scripted({"ok": 1}))
    assert resp.data == {"ok": 1}
    assert ledger.calls == 1 and ledger.in_tokens == 10 and ledger.out_tokens == 5


@pytest.mark.parametrize("kind", ["timeout", "network"])
def test_transient_retries_once_then_succeeds(kind):
    p = Scripted(ProviderFailure(kind), {"ok": 1})
    (resp, _), ledger, _ = run(p)
    assert resp.data == {"ok": 1} and ledger.calls == 2  # retry cũng được đếm


def test_timeout_twice_raises_ai_timeout_after_exactly_two_requests():
    p = Scripted(ProviderFailure("timeout"), ProviderFailure("timeout"))
    ledger = InMemoryLedger()
    with pytest.raises(AiTimeout):
        run(p, ledger)
    assert ledger.calls == 2 and len(p.calls) == 2


def test_429_backoff_with_jitter_then_success():
    p = Scripted(ProviderFailure("http", status=429), {"ok": 1})
    _, ledger, sleeps = run(p)
    assert ledger.calls == 2 and sleeps == [1.5]  # base 1.0 * (1 + rng 0.5)


@pytest.mark.parametrize("status", [500, 502, 503])
def test_5xx_retries_once_without_backoff(status):
    p = Scripted(ProviderFailure("http", status=status), {"ok": 1})
    _, ledger, sleeps = run(p)
    assert ledger.calls == 2 and sleeps == []


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_4xx_config_errors_never_retry(status):
    p = Scripted(ProviderFailure("http", status=status), {"ok": 1})
    ledger = InMemoryLedger()
    with pytest.raises(AiProviderError) as ei:
        run(p, ledger)
    assert ledger.calls == 1 and ei.value.status == status


def test_max_retries_is_clamped_to_one_even_if_config_says_more():
    p = Scripted(*[ProviderFailure("timeout")] * 5)
    ledger = InMemoryLedger()
    with pytest.raises(AiTimeout):
        run(p, ledger, max_retries=5)
    assert ledger.calls == 2


def test_max_retries_zero_disables_retry():
    p = Scripted(ProviderFailure("timeout"), {"ok": 1})
    ledger = InMemoryLedger()
    with pytest.raises(AiTimeout):
        run(p, ledger, max_retries=0)
    assert ledger.calls == 1


def _need_a(data):
    if "a" not in data:
        raise ValueError("thiếu a")
    return data["a"]


def test_schema_invalid_retries_with_feedback_then_succeeds():
    p = Scripted({"x": 1}, {"a": 7})
    (resp, parsed), ledger, _ = run(p, validate=_need_a)
    assert parsed == 7 and ledger.calls == 2
    retry_msgs = p.calls[1]
    assert retry_msgs[:2] == MSGS and "thiếu a" in retry_msgs[-1]["content"]
    assert len(p.calls[0]) == 2  # request đầu không bị đổi


def test_schema_invalid_twice_raises_output_invalid():
    p = Scripted({"x": 1}, {"y": 2})
    ledger = InMemoryLedger()
    with pytest.raises(AiOutputInvalid):
        run(p, ledger, validate=_need_a)
    assert ledger.calls == 2


def test_invalid_json_from_provider_is_retried_then_output_invalid():
    p = Scripted(ProviderFailure("invalid_json"), ProviderFailure("invalid_json"))
    with pytest.raises(AiOutputInvalid):
        run(p)


def test_before_call_exception_stops_before_any_request():
    class Exhausted:
        def before_call(self):
            raise AiProviderError("QUOTA_EXHAUSTED")

        def after_call(self, *a, **k):
            raise AssertionError("không được gọi")

    p = Scripted({"ok": 1})
    with pytest.raises(AiProviderError):
        run(p, Exhausted())
    assert p.calls == []  # không gửi gì ra ngoài


def test_error_message_never_contains_prompt_or_body():
    secret = "NỘI DUNG HỢP ĐỒNG BÍ MẬT"
    p = Scripted(ProviderFailure("http", status=500, detail=secret), ProviderFailure("http", status=500, detail=secret))
    with pytest.raises(AiProviderError) as ei:
        asyncio.run(
            call_with_retry(p, InMemoryLedger(), model_id="m",
                            messages=[{"role": "user", "content": secret}],
                            response_schema=SCHEMA, timeout_s=30, sleep=lambda s: asyncio.sleep(0))
        )
    assert secret not in str(ei.value)
