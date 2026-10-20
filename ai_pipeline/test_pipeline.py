import json
import sys
from pathlib import Path

# Tạm thời (C-17 sẽ chuyển sang pytest): cho phép import `app.*` khi chạy script từ ai_pipeline/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.clause.taxonomy import validate_labels  # noqa: E402
from utils.text_processing import document_router  # noqa: E402

# 1. Input: Văn bản hợp đồng thô (giả lập từ OCR/PDF)
RAW_CONTRACT_TEXT = """CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc

HỢP ĐỒNG LAO ĐỘNG

Điều 1. Chức danh và Công việc
Người lao động đảm nhận vị trí Lập trình viên. Người lao động không được phép tự ý sao chép mã nguồn của công ty.
Trong trường hợp nghỉ việc, không được làm việc cho đối thủ cạnh tranh trong vòng 24 tháng.

Điều 2. Thời giờ làm việc
Người lao động làm việc 8 tiếng một ngày, từ thứ 2 đến thứ 6."""

def run():
    print("🚀 BẮT ĐẦU CHẠY PIPELINE CLAUSE AI (smoke legacy — sẽ chuyển pytest ở C-17)\n")
    print("-" * 50)

    # BƯỚC 1: Đưa qua Structure-Aware Router để quyết định hướng cắt
    print("[1] Phân tích cấu trúc tài liệu...")
    route_decision = document_router(RAW_CONTRACT_TEXT)
    print(f"    -> Quyết định định tuyến: {route_decision}")

    # BƯỚC 2: Cắt ranh giới và Phân loại (Đang dùng Mock Output giả lập model LLM trả về)
    # Sang tuần sau, bước này sẽ được thay bằng LLM (GPT-4o-mini hoặc Qwen)
    print("\n[2] Giả lập LLM Cắt (Segmentation) và Phân loại (Classification)...")
    mock_llm_extracted_clauses = [
        {
            "clause_id": "cl_0001",
            "clause_number": "Điều 1",
            "span": {"start_char": 94, "end_char": 313},
            "original_text": "Người lao động đảm nhận vị trí Lập trình viên. Trong trường hợp nghỉ việc, không được làm việc cho đối thủ cạnh tranh trong vòng 24 tháng.",
            # LLM dự đoán 1..3 nhãn, nhãn chính đứng đầu (không còn điểm tự tin)
            "clause_labels": ["JOB_INFO", "EMPLOYEE_OBLIGATIONS_DISCIPLINE"],
        },
        {
            "clause_id": "cl_0002",
            "clause_number": "Điều 2",
            "span": {"start_char": 315, "end_char": 409},
            "original_text": "Người lao động làm việc 8 tiếng một ngày, từ thứ 2 đến thứ 6.",
            "clause_labels": ["WORKING_TIME"],
        }
    ]
    print(f"    -> Đã cắt thành công {len(mock_llm_extracted_clauses)} clauses.")

    # BƯỚC 3: Kiểm nhãn theo taxonomy (1..3 nhãn, thuộc 12 nhãn, không trùng)
    print("\n[3] Kiểm tra clause_labels theo taxonomy...")

    final_output = {
        "total_clauses": len(mock_llm_extracted_clauses),
        "clauses": [],
    }

    for clause in mock_llm_extracted_clauses:
        clause["clause_labels"] = validate_labels(clause["clause_labels"])
        final_output["clauses"].append(clause)

    # BƯỚC 4: Xuất ra JSON (định dạng legacy — chưa phải clause_output_v3)
    print("\n[4] 🎯 KẾT QUẢ FINAL JSON GIAO TIẾP VỚI BACKEND/RISK AI:")
    print("-" * 50)
    print(json.dumps(final_output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    run()