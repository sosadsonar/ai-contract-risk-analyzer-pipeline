import json
from config.thresholds import compute_clause_routing
from utils.text_processing import document_router

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
    print("🚀 BẮT ĐẦU CHẠY PIPELINE CLAUSE AI (TUẦN 1)\n")
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
            "clause_id": "clause_1",
            "clause_number": "Điều 1",
            "span": {"start_char": 94, "end_char": 313},
            "original_text": "Người lao động đảm nhận vị trí Lập trình viên. Trong trường hợp nghỉ việc, không được làm việc cho đối thủ cạnh tranh trong vòng 24 tháng.",
            # LLM dự đoán 2 nhãn và xuất ra độ tự tin (type_scores)
            "type_scores": {
                "JOB_DUTIES": 0.98,
                "CONFIDENTIALITY_IP": 0.85, 
                "TERMINATION": 0.45
            }
        },
        {
            "clause_id": "clause_2",
            "clause_number": "Điều 2",
            "span": {"start_char": 315, "end_char": 409},
            "original_text": "Người lao động làm việc 8 tiếng một ngày, từ thứ 2 đến thứ 6.",
            "type_scores": {
                "WORKING_HOURS_LEAVE": 0.92
            }
        }
    ]
    print(f"    -> Đã cắt thành công {len(mock_llm_extracted_clauses)} clauses.")

    # BƯỚC 3: Đưa qua logic tính toán Routing Rủi ro (Tấm khiên bi quan)
    print("\n[3] Áp dụng Risk Thresholds (Tấm khiên bi quan)...")
    
    final_output = {
        "contract_id": "TEST-DOC-001",
        "total_clauses": len(mock_llm_extracted_clauses),
        "clauses": []
    }

    for clause in mock_llm_extracted_clauses:
        # Gọi hàm logic từ config/thresholds.py
        routing_info = compute_clause_routing(clause["type_scores"])
        
        # Cập nhật thông tin vào clause
        clause["clause_type"] = list(clause["type_scores"].keys())
        clause.update(routing_info)
        final_output["clauses"].append(clause)

    # BƯỚC 4: Xuất ra JSON chuẩn Schema v2
    print("\n[4] 🎯 KẾT QUẢ FINAL JSON GIAO TIẾP VỚI BACKEND/RISK AI:")
    print("-" * 50)
    print(json.dumps(final_output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    run()