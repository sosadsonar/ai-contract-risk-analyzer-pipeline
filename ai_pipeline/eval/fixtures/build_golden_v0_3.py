"""
Sinh `golden_v0.3.json` từ dữ liệu THẬT: raw_text đọc từ file .txt (đã convert
từ .doc bằng LibreOffice) + offset đọc từ cột start_offset/end_offset trong
clauses_v02.csv (do Người 2 bổ sung).

KHÁC với build_golden_v0_2.py: file đó hardcode raw_text ngay trong code
(dict CONTRACTS), không đọc file nào cả — chỉ hợp cho data tự bịa để test
schema. Script này đọc dữ liệu thật từ disk, không tự bịa/tự đoán offset.

Yêu cầu trước khi chạy (phải có sẵn từ PR data/add-raw-text-and-offsets):
- ai_pipeline/data/data/processed/raw_text/<contract_id>.txt   (UTF-8, 1 file/hợp đồng)
- ai_pipeline/data/data/processed/clauses_v02.csv              (đã có cột start_offset,
  end_offset — nếu Người 2 chưa thêm 2 cột này thì script sẽ báo thiếu offset
  cho toàn bộ clause và không ghi được golden set nào)

Cách chạy:
    cd ai_pipeline
    python eval/fixtures/build_golden_v0_3.py

CẤU TRÚC PATH: submodule `data` được mount tại ai_pipeline/data/ và bản thân repo
`data` có thư mục con `data/`, nên file nằm ở ai_pipeline/data/data/processed/...
File golden_v0.3.json được ghi vào eval/fixtures/ (NGOÀI submodule) để commit ở repo code.
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

# eval/fixtures/build_golden_v0_3.py -> parents[2] = thư mục ai_pipeline/
AI_PIPELINE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = AI_PIPELINE_DIR / "data" / "data"   # submodule (ai_pipeline/data) + thư mục con data/
RAW_TEXT_DIR = DATA_DIR / "processed" / "raw_text"
CLAUSES_CSV = DATA_DIR / "processed" / "clauses_v02.csv"
OUT_PATH = Path(__file__).parent / "golden_v0.3.json"


def load_clauses_by_contract() -> dict[str, list[dict]]:
    """Đọc CSV, dùng utf-8-sig để tự bỏ BOM (contracts_metadata.csv/clauses CSV
    bên repo data có BOM ở đầu file)."""
    clauses_by_contract: dict[str, list[dict]] = defaultdict(list)
    with open(CLAUSES_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            clauses_by_contract[row["contract_id"]].append(row)
    return clauses_by_contract


def build_contract(contract_id: str, rows: list[dict]) -> dict:
    raw_path = RAW_TEXT_DIR / f"{contract_id}.txt"
    if not raw_path.exists():
        raise FileNotFoundError(
            f"[{contract_id}] Không tìm thấy {raw_path} — chạy script convert "
            f".doc -> .docx -> .txt trước (xem PR data/add-raw-text-and-offsets)."
        )
    raw_text = raw_path.read_text(encoding="utf-8")

    gold_clauses = []
    skipped: list[str] = []

    for row in rows:
        start_str = (row.get("start_offset") or "").strip()
        end_str = (row.get("end_offset") or "").strip()

        # Clause chưa có offset (Người 2 chưa điền, hoặc cố tình để trống vì
        # cần review tay — ví dụ các clause bị tách theo Rule 1 trong
        # clause_taxonomy_v02.md) -> bỏ qua thay vì đoán bừa.
        if not start_str or not end_str:
            skipped.append(row["clause_id"])
            continue

        start, end = int(start_str), int(end_str)
        sliced = raw_text[start:end]
        expected = row["clause_text"]

        # Bất biến quan trọng nhất, giống hệt build_golden_v0_2.py: offset phải
        # trỏ đúng y hệt clause_text gốc. Khác ở chỗ KHÔNG assert cứng (data
        # thật có thể còn lệch vài dòng cần Người 2 sửa) -> warning + loại khỏi
        # golden set, không cho crash toàn bộ script.
        if sliced != expected:
            skipped.append(row["clause_id"])
            print(
                f"⚠️  [{contract_id}] Offset lệch ở {row['clause_id']}: "
                f"raw_text[{start}:{end}] = {sliced!r} != clause_text = {expected!r}"
            )
            continue

        gold_clauses.append(
            {
                "clause_id": row["clause_id"],
                "start_offset": start,
                "end_offset": end,
                # CSV hiện tại là 1 dòng = 1 nhãn (single-label per row), nên
                # ở đây label luôn là list 1 phần tử. Nếu sau này CSV hỗ trợ
                # multi-label thật (nhiều nhãn cho cùng 1 span), cần đổi lại
                # cách gom nhóm ở load_clauses_by_contract() cho đúng.
                "label": [row["clause_type"]],
            }
        )

    if skipped:
        print(f"ℹ️  [{contract_id}] Bỏ qua {len(skipped)} clause: {skipped}")

    return {"contract_id": contract_id, "raw_text": raw_text, "gold_clauses": gold_clauses}


def main():
    clauses_by_contract = load_clauses_by_contract()
    dataset = [build_contract(cid, rows) for cid, rows in clauses_by_contract.items()]

    total_clauses = sum(len(c["gold_clauses"]) for c in dataset)
    total_rows = sum(len(rows) for rows in clauses_by_contract.values())
    total_skipped = total_rows - total_clauses

    OUT_PATH.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        f"\n✅ Đã ghi {OUT_PATH} — {len(dataset)} hợp đồng, "
        f"{total_clauses} clause hợp lệ, {total_skipped} clause bị bỏ qua "
        f"(thiếu offset hoặc offset lệch — cần Người 2 kiểm tra lại)."
    )


if __name__ == "__main__":
    main()
