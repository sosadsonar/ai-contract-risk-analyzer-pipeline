"""Test gọi LLM THẬT (Gemini) — chỉ chạy khi chọn rõ `-m llm` và có GEMINI_API_KEY.

Mặc định `pytest` BỎ QUA (addopts có `-m "not llm"`), nên CI thường và máy dev không tốn quota.
Chỉ dùng văn bản TỔNG HỢP, không có PII (AI_CONTEXT §3: không gửi hợp đồng thật ra ngoài).

Đang test service legacy `extract_clauses` (cầu nối tới C-01 b). Khi có `classify()`, thêm test
cho nó ở đây. Kết quả được ghi ra file ở $LLM_RESULT_PATH (nếu đặt) để CI hiển thị/tải về.
"""

import json
import os
import sys
from pathlib import Path

import pytest
from app.clause.taxonomy import validate_labels

pytestmark = [
    pytest.mark.llm,
    pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="thiếu GEMINI_API_KEY"),
]

SYNTHETIC_CONTRACT = """HỢP ĐỒNG LAO ĐỘNG

Điều 1. Chức danh và công việc
Người lao động đảm nhận vị trí Lập trình viên tại văn phòng của Công ty.

Điều 2. Thời giờ làm việc
Người lao động làm việc 8 tiếng một ngày, từ thứ Hai đến thứ Sáu.

Điều 3. Tiền lương
Mức lương cơ bản là 15.000.000 đồng/tháng, trả vào ngày 05 hằng tháng."""


def test_gemini_returns_valid_clause_labels():
    # Service legacy import kiểu `from services...`: cần ai_pipeline/ trên sys.path.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ai_pipeline"))
    from services.clause_extraction_service import extract_clauses

    result = extract_clauses(SYNTHETIC_CONTRACT, provider="gemini", contract_id="CI-SYNTHETIC")

    assert result["total_clauses"] >= 1
    for clause in result["clauses"]:
        validate_labels(clause["clause_labels"])  # 1..3 nhãn, thuộc taxonomy, không trùng

    out = os.getenv("LLM_RESULT_PATH")
    if out:
        Path(out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
