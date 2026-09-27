"""
Client thống nhất cho các LLM "free" dùng trong pipeline Clause AI:

- GeminiClient: gọi Google Gemini API (có free tier, cần GEMINI_API_KEY lấy tại
  https://aistudio.google.com/apikey). Dùng REST trực tiếp qua `requests`,
  không cần cài SDK riêng.
- QwenOllamaClient: gọi Qwen2.5 chạy local qua Ollama (https://ollama.com),
  hoàn toàn miễn phí, không cần API key, nhưng cần máy đã cài Ollama và đã
  `ollama pull qwen2.5:7b` (hoặc bản nhỏ hơn như `qwen2.5:3b` nếu máy yếu).

Cả hai client đều implement `generate_json(system_prompt, user_prompt) -> dict`
để phía service layer (clause_extraction_service.py) dùng chung một interface,
không cần biết đang chạy provider nào.
"""

import json
import os
from typing import Optional

import requests


class LLMClientError(Exception):
    """Lỗi khi gọi LLM hoặc khi LLM không trả về JSON hợp lệ."""


def _safe_json_parse(text: str) -> dict:
    """Một số model vẫn bọc JSON trong ```json ... ``` dù đã yêu cầu JSON thuần.
    Hàm này cố gắng bóc tách trước khi parse, và báo lỗi rõ ràng nếu vẫn fail."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise LLMClientError(
            f"Model không trả về JSON hợp lệ. Nội dung nhận được (300 ký tự đầu): {text[:300]!r}"
        ) from e


class BaseLLMClient:
    provider_name = "base"

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        raise NotImplementedError


class GeminiClient(BaseLLMClient):
    """Gọi Google Gemini API (free tier).

    Lấy API key miễn phí tại: https://aistudio.google.com/apikey
    Free tier hiện tại (kiểm tra lại quota thực tế trên trang Google AI Studio,
    có thể thay đổi theo thời gian): giới hạn số request/phút và request/ngày,
    đủ dùng để test pipeline ở quy mô đồ án (vài chục request/ngày).
    """

    provider_name = "gemini"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise LLMClientError(
                "Thiếu GEMINI_API_KEY. Lấy key miễn phí tại "
                "https://aistudio.google.com/apikey rồi thêm vào file .env "
                "(xem .env.example)."
            )
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self.endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )

    def generate_json(self, system_prompt: str, user_prompt: str, timeout: int = 60) -> dict:
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        }
        try:
            resp = requests.post(
                self.endpoint,
                params={"key": self.api_key},
                json=payload,
                timeout=timeout,
            )
        except requests.RequestException as e:
            raise LLMClientError(f"Không kết nối được tới Gemini API: {e}") from e

        if resp.status_code != 200:
            raise LLMClientError(
                f"Gemini API trả lỗi HTTP {resp.status_code}: {resp.text[:500]}"
            )

        data = resp.json()
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as e:
            raise LLMClientError(
                f"Phản hồi Gemini không đúng cấu trúc mong đợi: {data}"
            ) from e

        return _safe_json_parse(text)


class QwenOllamaClient(BaseLLMClient):
    """Gọi Qwen2.5 chạy local qua Ollama — miễn phí hoàn toàn, không cần API key.

    Yêu cầu:
      1. Cài Ollama: https://ollama.com/download
      2. Pull model:  `ollama pull qwen2.5:7b`  (máy yếu hơn dùng `qwen2.5:3b`)
      3. Chạy server (thường tự chạy sau khi cài):  `ollama serve`
    """

    provider_name = "qwen_ollama"

    def __init__(self, model: Optional[str] = None, host: Optional[str] = None):
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")

    def generate_json(self, system_prompt: str, user_prompt: str, timeout: int = 120) -> dict:
        try:
            import ollama
        except ImportError as e:
            raise LLMClientError(
                "Chưa cài package `ollama`. Chạy: pip install ollama"
            ) from e

        client = ollama.Client(host=self.host)
        try:
            response = client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                format="json",
                options={"temperature": 0.1},
            )
        except Exception as e:
            raise LLMClientError(
                f"Không gọi được Ollama tại {self.host} với model '{self.model}'. "
                f"Kiểm tra: đã `ollama serve` và `ollama pull {self.model}` chưa? "
                f"Chi tiết lỗi: {e}"
            ) from e

        content = response["message"]["content"]
        return _safe_json_parse(content)


def get_llm_client(provider: Optional[str] = None) -> BaseLLMClient:
    """Factory: chọn client theo tên provider hoặc theo env var LLM_PROVIDER.

    provider hợp lệ: "gemini" | "qwen" | "qwen_ollama" | "ollama"
    """
    provider = (provider or os.getenv("LLM_PROVIDER", "gemini")).lower()
    if provider == "gemini":
        return GeminiClient()
    if provider in ("qwen", "qwen_ollama", "ollama"):
        return QwenOllamaClient()
    raise LLMClientError(
        f"Provider không được hỗ trợ: '{provider}'. Dùng 'gemini' hoặc 'qwen_ollama'."
    )
