"""Test gọi LLM THẬT (Gemini) qua adapter mới — chỉ chạy khi chọn rõ `-m llm` và có GEMINI_API_KEY.

Mặc định `pytest` BỎ QUA (addopts có `-m "not llm and not llm_local"`), nên CI thường và máy dev không tốn quota.
Chỉ dùng văn bản TỔNG HỢP, không có PII (AI_CONTEXT §3: không gửi hợp đồng thật ra ngoài).
Kết quả được ghi ra $LLM_RESULT_PATH (nếu đặt) để job `llm-live` hiển thị/tải về.
"""

import asyncio
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.ai.clause_adapter import classify_clauses
from app.ai.gemini_client import GeminiProductClient
from app.ai.provider import InMemoryLedger
from app.ai.risk_adapter import analyze_risks
from app.clause.taxonomy import validate_labels
from app.risk.taxonomy import RISK_LABEL_SET

from tests.llm._synthetic import CLAUSES, RISK_CANDIDATES, RISK_ITEMS

pytestmark = [
    pytest.mark.llm,
    pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="thiếu GEMINI_API_KEY"),
]

MODEL = os.getenv("GEMINI_MODEL_ID") or os.getenv("GEMINI_MODEL") or "gemini-2.5-flash"
CFG = SimpleNamespace(
    GEMINI_MODEL_ID=MODEL, CLAUSE_BATCH_SIZE=20, RISK_BATCH_SIZE=6, LLM_PARALLELISM=2, LLM_TIMEOUT_SECONDS=30,
    LLM_AUTO_RETRY=1,
)


def _write(name: str, payload: dict) -> None:
    out = os.getenv("LLM_RESULT_PATH")
    if out:
        path = Path(out)
        data = json.loads(path.read_text("utf-8")) if path.exists() else {}
        data[name] = payload
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _provider():
    return GeminiProductClient(os.environ["GEMINI_API_KEY"], temperature=0.0)


def test_gemini_returns_valid_clause_labels():
    ledger = InMemoryLedger()
    out = asyncio.run(classify_clauses(CLAUSES, _provider(), ledger, CFG))
    assert [i.clause_id for i in out.items] == [c.clause_id for c in CLAUSES]
    for item in out.items:
        validate_labels(item.clause_labels)  # 1..3 nhãn, thuộc taxonomy, không trùng
    _write("clause", {"model": MODEL, "calls": ledger.calls, **out.to_dict()})


def test_gemini_risk_output_is_valid():
    ledger = InMemoryLedger()
    out = asyncio.run(analyze_risks("EMPLOYEE", RISK_ITEMS, RISK_CANDIDATES, _provider(), ledger, CFG))
    for it in out.items:
        assert set(it.risk_labels) <= RISK_LABEL_SET
    _write("risk", {"model": MODEL, "calls": ledger.calls, "citations_outside_candidate": out.citations_outside_candidate,  # noqa: E501
                    **out.to_dict()})
