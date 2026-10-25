import json
import sys
from pathlib import Path

# Tạm thời (C-17 sẽ chuyển sang pytest): cho phép import `app.*` khi chạy script từ ai_pipeline/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.clause.segmenter import segment  # noqa: E402
from app.clause.taxonomy import validate_labels  # noqa: E402
from app.privacy.masker import mask  # noqa: E402

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

    # BƯỚC 1: Che PII (toàn bộ canonical text, trước segmentation — INV-01)
    print("[1] Che PII...")
    masked = mask(RAW_CONTRACT_TEXT)
    print(f"    -> {len(masked.pii_spans)} span PII; độ dài giữ nguyên: "
          f"{len(masked.masked_text) == len(RAW_CONTRACT_TEXT)}")

    # BƯỚC 2: Cắt clause bằng luật local (C-01 a / C-02): không còn router, không gọi LLM
    print("\n[2] Segmentation (structure_parser + fallback paragraph)...")
    seg = segment(RAW_CONTRACT_TEXT, masked.masked_text, masked.pii_spans)
    print(f"    -> Đã cắt {len(seg.clauses)} clauses (segmentation {seg.segmentation_version}).")

    # BƯỚC 3: Phân loại — giả lập LLM #1 (nhãn cố định theo số điều). Bước thật là C-01 (b).
    print("\n[3] Giả lập Clause Classification + kiểm clause_labels theo taxonomy...")
    mock_labels = {
        "1": ["JOB_INFO", "EMPLOYEE_OBLIGATIONS_DISCIPLINE"],
        "2": ["WORKING_TIME"],
    }
    final_output = {"total_clauses": len(seg.clauses), "clauses": []}
    for clause in seg.clauses:
        labels = mock_labels.get(clause.structure.number, ["OTHER"])
        final_output["clauses"].append(
            {
                "clause_id": clause.clause_id,
                "clause_number": clause.structure.number,
                "span": {"start_char": clause.start_char, "end_char": clause.end_char},
                "original_text": clause.original_text,
                "clause_labels": validate_labels(labels),
            }
        )

    # BƯỚC 4: Xuất ra JSON (định dạng legacy — chưa phải clause_output_v3)
    print("\n[4] 🎯 KẾT QUẢ FINAL JSON GIAO TIẾP VỚI BACKEND/RISK AI:")
    print("-" * 50)
    print(json.dumps(final_output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
