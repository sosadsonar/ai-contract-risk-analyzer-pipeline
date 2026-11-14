"""Test model CỤC BỘ thật qua Ollama — chỉ chạy khi chọn rõ `-m llm_local`, có OLLAMA_MODEL và Ollama đang chạy.

    OLLAMA_MODEL=qwen2.5:7b-instruct pytest -m llm_local tests/llm/test_llm_local.py -s

Mục đích: kiểm adapter + schema + prompt với model nhỏ ở máy dev, không tốn quota Gemini. Model nhỏ có thể
trả nội dung kém nên test chỉ khẳng định HỢP ĐỒNG (cấu trúc, nhãn thuộc taxonomy, ID khớp), không khẳng
định chất lượng nhãn. Chỉ APP_ENV=dev, chỉ văn bản tổng hợp (TDD §13.4). Kết quả ghi ra $LLM_RESULT_PATH nếu đặt.
"""

import asyncio
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.ai.clause_adapter import classify_clauses
from app.ai.dev_local_client import DevLocalClient
from app.ai.provider import InMemoryLedger
from app.ai.risk_adapter import analyze_risks
from app.clause.taxonomy import validate_labels
from app.risk.taxonomy import RISK_LABEL_SET

from tests.llm._synthetic import CLAUSES, RISK_CANDIDATES, RISK_ITEMS

BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL = os.getenv("OLLAMA_MODEL")


def _ollama_up() -> bool:
    try:
        import requests

        return requests.get(f"{BASE_URL}/api/tags", timeout=2).status_code == 200
    except Exception:
        return False


pytestmark = [
    pytest.mark.llm_local,
    pytest.mark.skipif(not MODEL, reason="thiếu OLLAMA_MODEL"),
    pytest.mark.skipif(bool(MODEL) and not _ollama_up(), reason=f"Ollama không chạy ở {BASE_URL}"),
]

CFG = SimpleNamespace(
    GEMINI_MODEL_ID=MODEL, CLAUSE_BATCH_SIZE=20, RISK_BATCH_SIZE=6, LLM_PARALLELISM=1,
    LLM_TIMEOUT_SECONDS=int(os.getenv("OLLAMA_TIMEOUT", "180")), LLM_AUTO_RETRY=1,
)


def _write(name: str, payload: dict) -> None:
    out = os.getenv("LLM_RESULT_PATH")
    if out:
        path = Path(out)
        data = json.loads(path.read_text("utf-8")) if path.exists() else {}
        data[name] = payload
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_local_model_classifies_clauses_with_valid_contract():
    provider = DevLocalClient(app_env="dev", base_url=BASE_URL)
    ledger = InMemoryLedger()
    out = asyncio.run(classify_clauses(CLAUSES, provider, ledger, CFG))
    assert [i.clause_id for i in out.items] == [c.clause_id for c in CLAUSES]
    for item in out.items:
        validate_labels(item.clause_labels)
    assert ledger.calls >= 1
    _write("clause", {"model": MODEL, "calls": ledger.calls, **out.to_dict()})


def test_local_model_risk_output_passes_validation():
    provider = DevLocalClient(app_env="dev", base_url=BASE_URL)
    ledger = InMemoryLedger()
    out = asyncio.run(analyze_risks("EMPLOYEE", RISK_ITEMS, RISK_CANDIDATES, provider, ledger, CFG))
    for it in out.items:  # có thể rỗng nếu model cho là không rủi ro; nếu có thì phải hợp lệ
        assert set(it.risk_labels) <= RISK_LABEL_SET
        assert it.clause_id in {i.clause_id for i in RISK_ITEMS}
    assert out.prompt_version.startswith("risk_prompt_v2+")
    _write("risk", {"model": MODEL, "calls": ledger.calls, "citations_outside_candidate": out.citations_outside_candidate,  # noqa: E501
                    **out.to_dict()})
