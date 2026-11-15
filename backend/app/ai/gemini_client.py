"""GeminiProductClient — provider bắt buộc cho demo/eval (paid tier, model ID tường minh, TDD §13.4).

Khác `ai_pipeline/services/llm_clients.py` (legacy, free tier):
  * API key đi qua HEADER `x-goog-api-key`, không bao giờ nằm trong URL/query (tránh lọt vào log proxy);
  * có `responseSchema` (structured output) + `responseMimeType=application/json`;
  * temperature cố định từ cấu hình (mặc định 0.0), timeout truyền theo từng lần gọi;
  * không retry ở đây — retry matrix nằm ở `provider.call_with_retry` để đếm ledger đúng từng request;
  * message lỗi không chứa body response/prompt (có thể chứa nội dung hợp đồng đã che).

⚠ Chưa được kiểm thử với Gemini thật (không có key/mạng khi viết): phần dịch JSON Schema → `responseSchema`
(`to_gemini_schema`) và tên trường REST phải được xác nhận bằng job `llm-live` trước MS-2.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Callable, Optional

from app.ai.provider import LLMResponse, ProviderFailure

DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

# Từ khóa JSON Schema mà responseSchema của Gemini không nhận (hoặc không có tác dụng): bỏ trước khi gửi.
# Việc từ chối field lạ/trùng/không thuộc enum là của adapter (INV-05), không dựa vào provider.
_DROP_KEYS = {"$schema", "$id", "$defs", "title", "additionalProperties", "uniqueItems", "pattern"}


def to_gemini_schema(schema: dict) -> dict:
    """Inline `$ref`/`$defs`, đổi `const` → `enum`, bỏ từ khóa không hỗ trợ, viết HOA kiểu dữ liệu."""
    defs = schema.get("$defs", {})

    def walk(node: Any) -> Any:
        if isinstance(node, list):
            return [walk(x) for x in node]
        if not isinstance(node, dict):
            return node
        if "$ref" in node:
            ref = node["$ref"]
            if not ref.startswith("#/$defs/") or ref[len("#/$defs/"):] not in defs:
                raise ValueError(f"$ref không hỗ trợ: {ref}")
            return walk(defs[ref[len("#/$defs/"):]])
        out: dict = {}
        for k, v in node.items():
            if k in _DROP_KEYS:
                continue
            if k == "const":
                out["enum"] = [v]
            elif k == "type" and isinstance(v, str):
                out[k] = v.upper()
            elif k in ("properties",):
                out[k] = {pk: walk(pv) for pk, pv in v.items()}
            else:
                out[k] = walk(v)
        return out

    return walk(schema)


def to_gemini_request(
    messages: list[dict], response_schema: dict, *, temperature: float
) -> dict:
    """role=system → systemInstruction; assistant → model; còn lại → user."""
    system_parts, contents = [], []
    for m in messages:
        part = {"text": m["content"]}
        if m["role"] == "system":
            system_parts.append(part)
        else:
            contents.append({"role": "model" if m["role"] == "assistant" else "user", "parts": [part]})
    body: dict = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "responseMimeType": "application/json",
            "responseSchema": to_gemini_schema(response_schema),
        },
    }
    if system_parts:
        body["systemInstruction"] = {"parts": system_parts}
    return body


@dataclass(frozen=True)
class Price:
    """Giá USD / 1M token cho một model, kèm nguồn và ngày hiệu lực (OI-05 §2.4). Không hard-code:
    lấy từ cấu hình sau khi đối chiếu trang giá chính thức của Google."""

    input_per_mtok: float
    output_per_mtok: float
    source: str = ""

    def cost(self, in_tokens: int, out_tokens: int) -> float:
        return (in_tokens * self.input_per_mtok + out_tokens * self.output_per_mtok) / 1_000_000


def _usage(payload: dict) -> tuple[Optional[int], Optional[int]]:
    """(input, output) token; thinking token tính là output. None nếu provider không trả usage."""
    usage = payload.get("usageMetadata") if isinstance(payload, dict) else None
    if not isinstance(usage, dict) or "promptTokenCount" not in usage:
        return None, None
    out = int(usage.get("candidatesTokenCount", 0) or 0) + int(usage.get("thoughtsTokenCount", 0) or 0)
    return int(usage.get("promptTokenCount", 0) or 0), out


def parse_gemini_response(payload: dict, model_id: str, price: Optional[Price] = None) -> LLMResponse:
    """Lấy text JSON ở candidate đầu; finishReason khác STOP (SAFETY, MAX_TOKENS...) = invalid_json.

    Usage/cost được gắn cả vào ProviderFailure để ledger không mất token của response lỗi."""
    in_tokens, out_tokens = _usage(payload)
    cost = price.cost(in_tokens, out_tokens) if price and in_tokens is not None else 0.0

    def fail(detail: str) -> ProviderFailure:
        return ProviderFailure("invalid_json", detail=detail, in_tokens=in_tokens,
                               out_tokens=out_tokens, cost=cost)

    try:
        cand = payload["candidates"][0]
        parts = cand["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts)
    except (KeyError, IndexError, TypeError):
        raise fail("thiếu candidates/parts") from None
    if cand.get("finishReason", "STOP") not in ("STOP", "FINISH_REASON_UNSPECIFIED"):
        raise fail(f"finishReason={cand.get('finishReason')}")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise fail("text không phải JSON") from None
    if not isinstance(data, dict):
        raise fail("JSON gốc không phải object")
    return LLMResponse(
        data=data,
        model_id=payload.get("modelVersion") or model_id,
        in_tokens=in_tokens or 0,
        out_tokens=out_tokens or 0,
        cost=cost,
        usage_known=in_tokens is not None,
    )


# transport(url, headers, json_body, timeout_s) -> (status_code, parsed_json_or_None)
Transport = Callable[[str, dict, dict, float], tuple]


def _requests_transport(url: str, headers: dict, body: dict, timeout_s: float):
    import requests  # import trễ: test không cần cài

    try:
        r = requests.post(url, headers=headers, json=body, timeout=timeout_s)
    except requests.Timeout:
        raise ProviderFailure("timeout") from None
    except requests.RequestException:
        raise ProviderFailure("network") from None
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, None


class GeminiProductClient:
    def __init__(
        self,
        api_key: Optional[str],
        *,
        temperature: float = 0.0,
        base_url: str = DEFAULT_BASE_URL,
        transport: Optional[Transport] = None,
        price: Optional[Price] = None,
    ) -> None:
        if not api_key:
            raise ValueError("Thiếu GEMINI_API_KEY")
        self._api_key = api_key
        self.temperature = temperature
        self.base_url = base_url.rstrip("/")
        self._transport = transport or _requests_transport
        self.price = price

    def __repr__(self) -> str:  # không để key lọt vào log/traceback
        return f"GeminiProductClient(temperature={self.temperature})"

    async def generate_structured(
        self, *, model_id: str, messages: list[dict], response_schema: dict, timeout_s: int
    ) -> LLMResponse:
        if not model_id:
            raise ValueError("model_id bắt buộc (không có model mặc định ngầm)")
        url = f"{self.base_url}/models/{model_id}:generateContent"
        headers = {"x-goog-api-key": self._api_key, "Content-Type": "application/json"}
        body = to_gemini_request(messages, response_schema, temperature=self.temperature)
        try:
            # `requests` chỉ giới hạn từng lần đọc socket, không phải tổng thời gian → thêm wait_for.
            status, payload = await asyncio.wait_for(
                asyncio.to_thread(self._transport, url, headers, body, float(timeout_s)),
                timeout=timeout_s + 2,
            )
        except asyncio.TimeoutError:
            raise ProviderFailure("timeout") from None
        if status != 200:
            raise ProviderFailure("http", status=status)  # không đính kèm body
        if not isinstance(payload, dict):
            raise ProviderFailure("invalid_json", detail="body không phải JSON")
        return parse_gemini_response(payload, model_id, self.price)
