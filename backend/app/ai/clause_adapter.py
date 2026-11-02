"""Clause Classification adapter — LLM #1 (TDD §13, C-01 (b) khung).

Trạng thái W3: KHUNG chạy được với provider mock/Gemini; chưa chạy trên D1 (T4), chưa nối orchestrator.
Bất biến:
  INV-04  ra ngoài chỉ có `clause_id` + masked_text (không role, canonical, offset, structure);
  INV-05  response có field lạ / thiếu / trùng / ID lạ / nhãn ngoài taxonomy ⇒ bị từ chối; retry ≤1 ⇒ AiOutputInvalid;
  model KHÔNG khai `model_id`/`prompt_version`/`taxonomy_version` — backend điền.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Callable, Optional

from app.ai.prompts.clause_v1 import (
    OUTPUT_SCHEMA_VERSION,
    RESPONSE_SCHEMA,
    build_messages,
    prompt_pin,
)
from app.ai.provider import CallLedger, LLMProvider, call_with_retry
from app.clause.taxonomy import DATA_TAXONOMY_VERSION, validate_labels
from app.domain.errors import AiOutputInvalid, StageCancelled

_CLAUSE_ID = re.compile(r"^cl_[0-9]{4}$")
_ITEM_KEYS = {"clause_id", "clause_labels"}


@dataclass(frozen=True)
class ClauseMasked:
    clause_id: str
    masked_text: str


@dataclass(frozen=True)
class ClauseLabelItem:
    clause_id: str
    clause_labels: list[str]


@dataclass(frozen=True)
class ClauseOutput:
    items: list[ClauseLabelItem]
    model_id: str
    prompt_version: str
    taxonomy_version: str
    schema_version: str = OUTPUT_SCHEMA_VERSION

    def to_dict(self) -> dict:
        """Đúng `clause_output_v3.json` (additionalProperties=false)."""
        return {
            "schema_version": self.schema_version,
            "items": [{"clause_id": i.clause_id, "clause_labels": list(i.clause_labels)} for i in self.items],
            "model_id": self.model_id,
            "prompt_version": self.prompt_version,
            "taxonomy_version": self.taxonomy_version,
        }


def make_batches(items: list, size: int) -> list[list]:
    if size <= 0:
        raise ValueError("batch size phải > 0")
    return [items[i : i + size] for i in range(0, len(items), size)]


def validate_batch_response(data: dict, expected_ids: list[str]) -> dict[str, list[str]]:
    """Kiểm một response; raise ValueError (message KHÔNG chứa nội dung clause) nếu sai.

    Trả {clause_id: labels}. Từ chối: field lạ ở gốc/item (confidence, type_scores, quote, span,
    start_char...), ID thiếu/trùng/lạ, nhãn ngoài taxonomy/trùng/ngoài 1..3.
    """
    if not isinstance(data, dict) or set(data) != {"items"}:
        extra = sorted(set(data) - {"items"}) if isinstance(data, dict) else []
        raise ValueError(f"response phải chỉ gồm 'items' (thừa: {extra})")
    items = data["items"]
    if not isinstance(items, list):
        raise ValueError("'items' phải là mảng")
    expected = set(expected_ids)
    out: dict[str, list[str]] = {}
    for it in items:
        if not isinstance(it, dict) or set(it) != _ITEM_KEYS:
            extra = sorted(set(it) - _ITEM_KEYS) if isinstance(it, dict) else []
            raise ValueError(f"item phải đúng {sorted(_ITEM_KEYS)} (thừa: {extra})")
        cid = it["clause_id"]
        if not isinstance(cid, str) or not _CLAUSE_ID.match(cid):
            raise ValueError("clause_id sai định dạng")
        if cid not in expected:
            raise ValueError(f"clause_id không có trong yêu cầu: {cid}")
        if cid in out:
            raise ValueError(f"clause_id trùng: {cid}")
        out[cid] = validate_labels(it["clause_labels"])  # ValueError nếu sai
    missing = [c for c in expected_ids if c not in out]
    if missing:
        raise ValueError(f"thiếu clause_id: {missing[:5]}")
    return out


async def classify_clauses(
    masked_items: list[ClauseMasked],
    provider: LLMProvider,
    ledger: CallLedger,
    cfg,
    cancel: Optional[Callable[[], bool]] = None,
) -> ClauseOutput:
    """Phân loại theo lô (CLAUSE_BATCH_SIZE), song song ≤ LLM_PARALLELISM, kiểm cancel TRƯỚC mỗi lô.

    `cancel()` trả True ⇒ raise StageCancelled (orchestrator quyết định state, ví dụ End).
    Lô lỗi ⇒ các lô còn lại bị hủy ngay; lỗi mang mã AI_* của lô đầu tiên thất bại.
    """
    if not masked_items:
        raise ValueError("không có clause để phân loại")
    ids = [m.clause_id for m in masked_items]
    if len(set(ids)) != len(ids):
        raise ValueError("clause_id đầu vào bị trùng")
    model_id = getattr(cfg, "GEMINI_MODEL_ID", None)
    if not model_id:
        raise ValueError("thiếu model id (GEMINI_MODEL_ID) — không dùng model mặc định ngầm")

    batches = make_batches(masked_items, cfg.CLAUSE_BATCH_SIZE)
    sem = asyncio.Semaphore(max(1, cfg.LLM_PARALLELISM))
    labels: dict[str, list[str]] = {}
    resp_model: dict[int, str] = {}

    async def run(idx: int, batch: list[ClauseMasked]) -> None:
        async with sem:
            if cancel is not None and cancel():
                raise StageCancelled()
            expected = [m.clause_id for m in batch]
            resp, parsed = await call_with_retry(
                provider,
                ledger,
                model_id=model_id,
                messages=build_messages([(m.clause_id, m.masked_text) for m in batch]),
                response_schema=RESPONSE_SCHEMA,
                timeout_s=cfg.LLM_TIMEOUT_SECONDS,
                validate=lambda data, e=expected: validate_batch_response(data, e),
                max_retries=cfg.LLM_AUTO_RETRY,
            )
            labels.update(parsed)
            resp_model[idx] = resp.model_id

    tasks = [asyncio.ensure_future(run(i, b)) for i, b in enumerate(batches)]
    try:
        await asyncio.gather(*tasks)
    except BaseException:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise

    if set(labels) != set(ids):  # phòng thủ: không thể xảy ra nếu validate đúng
        raise AiOutputInvalid("hợp nhất các lô không khớp tập clause_id")
    models = set(resp_model.values())
    return ClauseOutput(
        items=[ClauseLabelItem(cid, labels[cid]) for cid in ids],
        model_id=models.pop() if len(models) == 1 else model_id,
        prompt_version=prompt_pin(),
        taxonomy_version=DATA_TAXONOMY_VERSION,
    )
