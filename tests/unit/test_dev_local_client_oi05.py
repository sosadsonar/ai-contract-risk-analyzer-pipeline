
"""OI-05: preserve reported usage on invalid local JSON."""

import asyncio

import pytest
from app.ai.dev_local_client import DevLocalClient
from app.ai.provider import (
    AiOutputInvalid,
    InMemoryLedger,
    ProviderFailure,
    call_with_retry,
)


def response(content, in_tokens=120, out_tokens=40):
    return {
        "message": {"content": content},
        "prompt_eval_count": in_tokens,
        "eval_count": out_tokens,
    }


CASES = [
    (
        "valid_json",
        [response('{"ok": true}')],
        0,
        (1, 120, 40, [], "SUCCESS"),
    ),
    (
        "invalid_json_known_usage",
        [response('{"broken":')],
        0,
        (1, 120, 40, ["invalid_json"], "AiOutputInvalid"),
    ),
    (
        "non_object_json_known_usage",
        [response("[]")],
        0,
        (1, 120, 40, ["invalid_json"], "AiOutputInvalid"),
    ),
    (
        "invalid_json_retry_success",
        [
            response('{"broken":', 120, 40),
            response('{"ok": true}', 130, 50),
        ],
        1,
        (2, 250, 90, ["invalid_json"], "SUCCESS"),
    ),
    (
        "invalid_json_retry_exhausted",
        [
            response('{"broken":', 120, 40),
            response('{"broken":', 130, 50),
        ],
        1,
        (
            2, 250, 90,
            ["invalid_json", "invalid_json"],
            "AiOutputInvalid",
        ),
    ),
    (
        "missing_usage",
        [{"message": {"content": "broken"}}],
        0,
        (1, 0, 0, ["invalid_json"], "AiOutputInvalid"),
    ),
    (
        "partial_usage",
        [{
            "message": {"content": "broken"},
            "prompt_eval_count": 120,
        }],
        0,
        (1, 120, 0, ["invalid_json"], "AiOutputInvalid"),
    ),
    (
        "malformed_usage",
        [response("broken", True, -1)],
        0,
        (1, 0, 0, ["invalid_json"], "AiOutputInvalid"),
    ),
]


@pytest.mark.parametrize(
    "name,payloads,retry,expected",
    CASES,
    ids=[case[0] for case in CASES],
)
def test_ledger(name, payloads, retry, expected):
    iterator = iter(payloads)
    transport_calls = 0

    def fake_transport(url, body, timeout):
        nonlocal transport_calls
        transport_calls += 1
        return 200, next(iterator)

    client = DevLocalClient(
        app_env="dev",
        transport=fake_transport,
    )

    ledger = InMemoryLedger(max_calls=2)

    async def execute():
        outcome = "SUCCESS"

        try:
            result, _ = await call_with_retry(
                client,
                ledger,
                model_id="offline-test",
                messages=[
                    {
                        "role": "user",
                        "content": "Synthetic test",
                    }
                ],
                response_schema={"type": "object"},
                timeout_s=5,
                max_retries=retry,
            )
            assert result.data == {"ok": True}

        except AiOutputInvalid:
            outcome = "AiOutputInvalid"

        assert transport_calls == ledger.calls

        assert (
            ledger.calls,
            ledger.in_tokens,
            ledger.out_tokens,
            ledger.errors,
            outcome,
        ) == expected

    asyncio.run(execute())


@pytest.mark.parametrize(
    "payload,expected",
    [
        (response("broken", 120, 40), (120, 40, True)),
        (
            {"message": {"content": "broken"}},
            (None, None, False),
        ),
        (response("broken", 0, 0), (0, 0, True)),
        (response("broken", True, -1), (None, None, False)),
    ],
    ids=[
        "known_usage",
        "unknown_usage",
        "zero_usage",
        "malformed_usage",
    ],
)
def test_failure_metadata(payload, expected):
    client = DevLocalClient(
        app_env="dev",
        transport=lambda *args: (200, payload),
    )

    with pytest.raises(ProviderFailure) as captured:
        asyncio.run(
            client.generate_structured(
                model_id="offline-test",
                messages=[],
                response_schema={"type": "object"},
                timeout_s=5,
            )
        )

    exc = captured.value

    assert exc.kind == "invalid_json"

    assert (
        exc.in_tokens,
        exc.out_tokens,
        exc.usage_known,
    ) == expected


@pytest.mark.parametrize(
    "reported,expected",
    [((True, -3), (0, 0, False)), ((120, None), (120, 0, False)), ((0, 40), (0, 40, True)),
     (("120", {}), (0, 0, False))],
)
def test_success_reports_only_nonnegative_integer_usage(reported, expected):
    client = DevLocalClient(app_env="dev", transport=lambda *_: (200, response('{"ok": true}', *reported)))
    result = asyncio.run(client.generate_structured(model_id="fixture", messages=[], response_schema={}, timeout_s=1))
    assert (result.in_tokens, result.out_tokens, result.usage_known) == expected
