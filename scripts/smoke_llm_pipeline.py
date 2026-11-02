"""Manual-only smoke for the legacy Clause AI provider (not a product pipeline).

Run from the project root after configuring the provider in .env::

    python -m pip install -e '.[dev]'
    python scripts/smoke_llm_pipeline.py

This deliberately calls an external LLM and is excluded from pytest/CI. Use only
this synthetic, de-identified sample: the legacy extractor sends text unmasked.
Its output is NOT final_result_v1 and must not be served by the mock API.
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "ai_pipeline"))

from dotenv import load_dotenv  # noqa: E402

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


def main() -> None:
    load_dotenv(ROOT / ".env")
    provider = os.getenv("LLM_PROVIDER", "gemini")
    try:
        result = extract_clauses(RAW_CONTRACT_TEXT, provider=provider, contract_id="SYNTHETIC-SMOKE")
    except LLMClientError as error:
        raise SystemExit(f"Legacy provider smoke failed ({provider}): {error}") from error
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["unmatched_span_count"]:
        print(f"Warning: {result['unmatched_span_count']} clause spans did not match the sample exactly")


if __name__ == "__main__":
    main()
