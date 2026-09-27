"""
Chạy pipeline Clause AI với LLM THẬT (Gemini hoặc Qwen qua Ollama), thay cho
mock data trong test_pipeline.py.

Cách chạy (luôn chạy từ trong thư mục ai_pipeline/):

    cd ai_pipeline
    pip install -r requirements-hint.txt   # xem README hoặc pyproject.toml
    cp ../.env.example ../.env             # rồi điền GEMINI_API_KEY vào .env
    python test_llm_pipeline.py                    # dùng provider mặc định (gemini)
    LLM_PROVIDER=qwen_ollama python test_llm_pipeline.py   # dùng Qwen local

Yêu cầu:
  - Gemini: cần GEMINI_API_KEY (free, lấy tại https://aistudio.google.com/apikey)
  - Qwen/Ollama: cần cài Ollama + `ollama pull qwen2.5:7b`, không cần API key
"""

import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()  # đọc file .env ở thư mục gốc project nếu có

from services.clause_extraction_service import extract_clauses  # noqa: E402
from services.llm_clients import LLMClientError  # noqa: E402

RAW_CONTRACT_TEXT = """CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc

HỢP ĐỒNG LAO ĐỘNG

Điều 1. Chức danh và Công việc
Người lao động đảm nhận vị trí Lập trình viên. Người lao động không được phép tự ý sao chép mã nguồn của công ty.
Trong trường hợp nghỉ việc, không được làm việc cho đối thủ cạnh tranh trong vòng 24 tháng.

Điều 2. Thời giờ làm việc
Người lao động làm việc 8 tiếng một ngày, từ thứ 2 đến thứ 6."""


def run():
    provider = os.getenv("LLM_PROVIDER", "gemini")
    print(f"🚀 CHẠY PIPELINE VỚI LLM THẬT (provider={provider})\n")
    print("-" * 50)

    try:
        result = extract_clauses(RAW_CONTRACT_TEXT, provider=provider, contract_id="TEST-REAL-001")
    except LLMClientError as e:
        print(f"❌ Lỗi gọi LLM: {e}\n")
        print("Kiểm tra lại:")
        print("  - Gemini: đã set GEMINI_API_KEY trong file .env chưa?")
        print("  - Qwen/Ollama: đã `ollama serve` và `ollama pull qwen2.5:7b` chưa?")
        sys.exit(1)

    print("🎯 KẾT QUẢ JSON (chuẩn schema v2):")
    print("-" * 50)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["unmatched_span_count"] > 0:
        print(
            f"\n⚠️  Cảnh báo: {result['unmatched_span_count']} clause không định vị "
            f"được span chính xác (LLM có thể đã diễn giải lại text thay vì copy "
            f"nguyên văn). Cần xem lại prompt hoặc hậu xử lý."
        )


if __name__ == "__main__":
    run()
