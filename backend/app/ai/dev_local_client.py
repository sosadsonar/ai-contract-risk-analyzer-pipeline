"""DevLocalClient — Qwen/Ollama cục bộ, CHỈ `APP_ENV=dev` và dữ liệu đã de-identify (TDD §13.4).

Không dùng cho demo/eval; `validate_for_env` (core/config) đã chặn `DEV_LLM_PROVIDER=local` ngoài dev,
constructor chặn thêm một lớp nữa.
"""

from __future__ import annotations

import asyncio
import json
from typing import Callable, Optional

from app.ai.provider import LLMResponse, ProviderFailure

Transport = Callable[[str, dict, float], tuple]


def _requests_transport(url: str, body: dict, timeout_s: float):
    import requests

    try:
        r = requests.post(url, json=body, timeout=timeout_s)
    except requests.Timeout:
        raise ProviderFailure("timeout") from None
    except requests.RequestException:
        raise ProviderFailure("network") from None
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, None


class DevLocalClient:
    def __init__(
        self,
        *,
        app_env: str,
        base_url: str = "http://localhost:11434",
        temperature: float = 0.0,
        transport: Optional[Transport] = None,
    ) -> None:
        if app_env != "dev":
            raise ValueError("DevLocalClient chỉ được dùng khi APP_ENV=dev")
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self._transport = transport or _requests_transport

    async def generate_structured(
        self, *, model_id: str, messages: list[dict], response_schema: dict, timeout_s: int
    ) -> LLMResponse:
        body = {
            "model": model_id,
            "messages": messages,
            "stream": False,
            "format": response_schema,  # Ollama structured outputs nhận JSON Schema
            "options": {"temperature": self.temperature},
        }
        try:
            status, payload = await asyncio.wait_for(
                asyncio.to_thread(self._transport, f"{self.base_url}/api/chat", body, float(timeout_s)),
                timeout=timeout_s + 2,
            )
        except asyncio.TimeoutError:
            raise ProviderFailure("timeout") from None
        if status != 200:
            raise ProviderFailure("http", status=status)
        try:
            data = json.loads(payload["message"]["content"])
        except (KeyError, TypeError, json.JSONDecodeError):
            raise ProviderFailure("invalid_json") from None
        if not isinstance(data, dict):
            raise ProviderFailure("invalid_json")
        return LLMResponse(
            data=data,
            model_id=model_id,
            in_tokens=int(payload.get("prompt_eval_count", 0) or 0),
            out_tokens=int(payload.get("eval_count", 0) or 0),
        )
