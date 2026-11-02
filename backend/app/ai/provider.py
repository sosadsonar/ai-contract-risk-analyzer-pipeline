"""LLMProvider abstraction, CallLedger và retry matrix (TDD §13.4, C-07).

Quy tắc cứng:
  * MỖI request thật tới provider — kể cả retry — gọi `ledger.before_call()` TRƯỚC khi gửi và
    `ledger.after_call()` sau (kể cả khi lỗi). `before_call` được phép raise (hết quota) → dừng, không gửi.
  * Retry tự động tối đa `max_retries` (≤1) cho MỘT lần gọi, tính chung mọi loại lỗi:
    timeout/mạng, 429 (backoff + jitter), 5xx, response sai schema (kèm phản hồi lỗi validate).
    400/401/403 và các 4xx khác KHÔNG retry.
  * Không bao giờ đưa nội dung prompt/response, API key vào message lỗi hoặc log.
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional, Protocol

from app.domain.errors import AiOutputInvalid, AiProviderError, AiTimeout

MAX_AUTO_RETRY = 1  # TDD §4.1: LLM_AUTO_RETRY không vượt 1
BACKOFF_BASE_S = 1.0


@dataclass(frozen=True)
class LLMResponse:
    """Kết quả đã parse JSON từ provider. `data` chưa được tin: adapter phải validate."""

    data: dict
    model_id: str
    in_tokens: int = 0
    out_tokens: int = 0
    cost: float = 0.0


class ProviderFailure(Exception):
    """Lỗi tầng provider (chưa phân loại theo domain). `kind` ∈ timeout|network|http|invalid_json."""

    def __init__(self, kind: str, *, status: Optional[int] = None, detail: str = "") -> None:
        super().__init__(f"{kind}:{status}" if status else kind)
        self.kind = kind
        self.status = status
        self.detail = detail  # đã lọc: không chứa key/nội dung hợp đồng

    @property
    def retryable(self) -> bool:
        if self.kind in ("timeout", "network", "invalid_json"):
            return True
        return self.kind == "http" and self.status is not None and (
            self.status == 429 or 500 <= self.status <= 599
        )


class LLMProvider(Protocol):
    async def generate_structured(
        self, *, model_id: str, messages: list[dict], response_schema: dict, timeout_s: int
    ) -> LLMResponse: ...


class CallLedger(Protocol):
    def before_call(self) -> None: ...

    def after_call(
        self, in_tokens: int, out_tokens: int, cost: float, error_code: Optional[str] = None
    ) -> None: ...


@dataclass
class InMemoryLedger:
    """Ledger cho dev/test; bản thật (quota SQLite + RunLog) do N4 làm ở C-16."""

    calls: int = 0
    in_tokens: int = 0
    out_tokens: int = 0
    cost: float = 0.0
    errors: list[str] = field(default_factory=list)
    max_calls: Optional[int] = None

    def before_call(self) -> None:
        if self.max_calls is not None and self.calls >= self.max_calls:
            raise AiProviderError("QUOTA_EXHAUSTED")
        self.calls += 1

    def after_call(self, in_tokens, out_tokens, cost, error_code=None) -> None:
        self.in_tokens += in_tokens
        self.out_tokens += out_tokens
        self.cost += cost
        if error_code:
            self.errors.append(error_code)


def _domain_error(f: ProviderFailure) -> Exception:
    if f.kind == "timeout":
        return AiTimeout()
    if f.kind == "invalid_json":
        return AiOutputInvalid("provider không trả JSON hợp lệ")
    return AiProviderError(f.kind, status=f.status)


async def call_with_retry(
    provider: LLMProvider,
    ledger: CallLedger,
    *,
    model_id: str,
    messages: list[dict],
    response_schema: dict,
    timeout_s: int,
    validate: Optional[Callable[[dict], Any]] = None,
    max_retries: int = MAX_AUTO_RETRY,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    rng: Callable[[], float] = random.random,
) -> tuple[LLMResponse, Any]:
    """Gọi provider theo retry matrix. Trả (response, kết quả `validate`).

    `validate(data)` raise ValueError nếu response sai nội dung; lần retry sau thêm một message
    `user` mô tả lỗi (không chứa nội dung hợp đồng) để model sửa theo CÙNG schema.
    """
    max_retries = min(max(max_retries, 0), MAX_AUTO_RETRY)
    attempt = 0
    msgs = list(messages)
    while True:
        ledger.before_call()  # kể cả retry; có thể raise (quota) → không gửi
        try:
            resp = await provider.generate_structured(
                model_id=model_id, messages=msgs, response_schema=response_schema, timeout_s=timeout_s
            )
        except ProviderFailure as f:
            ledger.after_call(0, 0, 0.0, error_code=f"{f.kind}:{f.status}" if f.status else f.kind)
            if f.retryable and attempt < max_retries:
                attempt += 1
                if f.status == 429:  # backoff + jitter
                    await sleep(BACKOFF_BASE_S * (1 + rng()))
                continue
            raise _domain_error(f) from None
        ledger.after_call(resp.in_tokens, resp.out_tokens, resp.cost)
        if validate is None:
            return resp, None
        try:
            return resp, validate(resp.data)
        except ValueError as e:
            ledger.errors.append("schema_invalid") if isinstance(ledger, InMemoryLedger) else None
            if attempt < max_retries:
                attempt += 1
                msgs = list(messages) + [{
                    "role": "user",
                    "content": "Phản hồi trước không hợp lệ: " + str(e)[:300]
                    + ". Trả lại JSON đúng schema, chỉ gồm các trường được yêu cầu.",
                }]
                continue
            raise AiOutputInvalid(str(e)[:200]) from None
