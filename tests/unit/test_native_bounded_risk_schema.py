
import asyncio
import copy
import json
from types import SimpleNamespace

import pytest
from app.ai.dev_local_client import DevLocalClient
from app.ai.provider import (
    AiOutputInvalid,
    InMemoryLedger,
    LLMResponse,
)
from app.ai.risk_adapter import (
    RESPONSE_SCHEMA,
    RiskItemIn,
    analyze_risks,
)


def empty_output():
    return {
        "schema_version": "risk_output_v2",
        "items": [],
    }


def risk_output(
    length=600,
    clause_id="cl_0001",
):
    return {
        "schema_version": "risk_output_v2",
        "items": [{
            "clause_id": clause_id,
            "basis_type": "LEGAL_VIOLATION",
            "risk_labels": [
                "DEPOSIT_DOCUMENT_HELD"
            ],
            "citation_ids": [],
            "evidence_status": (
                "INSUFFICIENT_EVIDENCE"
            ),
            "explanation": "a" * length,
        }],
    }


class RecordingProvider:

    def __init__(self, responses):
        self.responses = iter(responses)
        self.schemas = []

    async def generate_structured(
        self, *, model_id, messages,
        response_schema, timeout_s
    ):
        self.schemas.append(
            copy.deepcopy(response_schema)
        )

        return LLMResponse(
            data=next(self.responses),
            model_id=model_id,
            in_tokens=10,
            out_tokens=5,
        )


def execute(
    responses,
    *,
    environment="dev",
    provider_name="local",
    local_client=True,
    batch_size=1,
    retries=0,
    ids=("cl_0001",),
):
    schemas = []
    iterator = iter(responses)

    def transport(url, body, timeout):
        schemas.append(
            copy.deepcopy(body["format"])
        )

        return 200, {
            "message": {
                "content": json.dumps(next(iterator))
            },
            "prompt_eval_count": 10,
            "eval_count": 5,
        }

    if local_client:
        provider = DevLocalClient(
            app_env="dev",
            transport=transport,
        )
    else:
        provider = RecordingProvider(responses)
        schemas = provider.schemas

    cfg = SimpleNamespace(
        APP_ENV=environment,
        DEV_LLM_PROVIDER=provider_name,
        GEMINI_MODEL_ID="offline-test",
        RISK_BATCH_SIZE=batch_size,
        LLM_PARALLELISM=1,
        LLM_AUTO_RETRY=retries,
        LLM_TIMEOUT_SECONDS=5,
    )

    items = [
        RiskItemIn(
            clause_id,
            "Synthetic employment clause.",
            ["EMPLOYEE_OBLIGATIONS_DISCIPLINE"],
            [],
        )
        for clause_id in ids
    ]

    ledger = InMemoryLedger()

    error = None
    result = None

    try:
        result = asyncio.run(
            analyze_risks(
                "EMPLOYEE",
                items,
                {},
                provider,
                ledger,
                cfg,
            )
        )
    except AiOutputInvalid as exc:
        error = exc

    return result, error, schemas, ledger


def test_native_dynamic_schema():
    original = copy.deepcopy(RESPONSE_SCHEMA)

    result, error, schemas, ledger = execute(
        [empty_output(), empty_output()],
        ids=("cl_0001", "cl_0002"),
    )

    assert error is None
    assert result is not None
    assert ledger.calls == 2

    for schema, clause_id in zip(
        schemas, ("cl_0001", "cl_0002")
    ):
        array = schema["properties"]["items"]
        fields = array["items"]["properties"]

        assert array["maxItems"] == 1
        assert fields["clause_id"]["enum"] == [
            clause_id
        ]
        assert fields["explanation"]["maxLength"] == 600

        assert array["items"]["required"] == (
            original["properties"]["items"]
            ["items"]["required"]
        )

    assert RESPONSE_SCHEMA == original
    assert schemas[0] != schemas[1]


def test_native_601_rejected():
    result, error, schemas, ledger = execute(
        [risk_output(601)]
    )

    assert isinstance(error, AiOutputInvalid)
    assert result is None
    assert ledger.calls == 1
    assert ledger.errors == ["schema_invalid"]


def test_native_long_output_retry():
    result, error, schemas, ledger = execute(
        [risk_output(601), empty_output()],
        retries=1,
    )

    assert error is None
    assert result is not None
    assert ledger.calls == 2
    assert ledger.errors == ["schema_invalid"]
    assert schemas[0] == schemas[1]


def test_native_600_accepted():
    result, error, schemas, ledger = execute(
        [risk_output(600)]
    )

    assert error is None
    assert result is not None
    assert ledger.calls == 1


def test_empty_output_remains_valid():
    result, error, schemas, ledger = execute(
        [empty_output()]
    )

    assert error is None
    assert result.to_dict()["items"] == []


@pytest.mark.parametrize(
    "payload",
    [
        risk_output(100, "cl_9999"),
        {
            "schema_version": "risk_output_v2",
            "items": [
                risk_output(100)["items"][0],
                risk_output(100)["items"][0],
            ],
        },
    ],
    ids=["unknown_clause", "duplicate_clause"],
)
def test_existing_validator_still_rejects(payload):
    result, error, schemas, ledger = execute(
        [payload]
    )

    assert result is None
    assert isinstance(error, AiOutputInvalid)


@pytest.mark.parametrize(
    "options",
    [
        {
            "environment": "prod",
            "local_client": False,
            "provider_name": "gemini",
        },
        {"local_client": False},
        {"provider_name": "fake"},
        {"environment": "prod"},
        {"batch_size": 4},
    ],
    ids=[
        "nonlocal_production",
        "nonlocal_dev",
        "provider_mode_guard",
        "environment_guard",
        "untested_batch_mode",
    ],
)
def test_legacy_schema_unchanged(options):
    original = copy.deepcopy(RESPONSE_SCHEMA)

    result, error, schemas, ledger = execute(
        [risk_output(601)],
        **options,
    )

    assert error is None
    assert result is not None
    assert schemas == [original]
    assert RESPONSE_SCHEMA == original
