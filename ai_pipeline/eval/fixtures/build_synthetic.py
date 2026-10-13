"""
Sinh `synthetic_v0.2.json` — bộ dữ liệu TỔNG HỢP (tự viết tay 6 hợp đồng giả) để
smoke-test eval_segmentation.py và pipeline mà KHÔNG cần data thật/submodule/API.

⚠️ Đây KHÔNG phải golden set. Golden set thật (từ HDLD001-003 của Người 2) nằm ở
ai_pipeline/data/ (submodule). Đừng dùng số liệu trên bộ này để báo cáo KPI.

Nhãn dùng taxonomy 12 nhãn (ai_pipeline/config/taxonomy.py). Nhãn được chuyển từ
taxonomy 8 nhãn cũ theo phán đoán của Người 1 (không có ai annotate lại), vì vậy
chỉ dùng bộ này để kiểm tra span/định dạng, không dùng để đo độ chính xác phân loại.

Khác dữ liệu thật: span ở đây BAO GỒM dòng tiêu đề "Điều X. ..." còn data thật
(Rule 6 trong clause_taxonomy_v02.md) chỉ lấy nội dung bên dưới heading.

Cách chạy (từ thư mục ai_pipeline/):
    python eval/fixtures/build_synthetic.py

Mở rộng: thêm hợp đồng vào CONTRACTS, KHÔNG tự tính offset — script tự tìm và kiểm tra
(assert raw[start:end] == block_text).
"""

import json
from pathlib import Path

HEADER = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập - Tự do - Hạnh phúc\n\nHỢP ĐỒNG LAO ĐỘNG\n\n"

# Mỗi contract là 1 list block: (clause_number, title, content, labels)
CONTRACTS = {
    "SYN-HD-002": [
        ("Điều 1", "Chức danh và Công việc",
         "Người lao động đảm nhận vị trí Nhân viên hành chính, làm việc tại văn phòng công ty.",
         ["JOB_INFO"]),
        ("Điều 2", "Thời giờ làm việc và nghỉ phép",
         "Người lao động làm việc 8 giờ/ngày, 5 ngày/tuần; được nghỉ phép năm 12 ngày có hưởng lương.",
         ["WORKING_TIME", "LEAVE"]),
        ("Điều 3", "Tiền lương",
         "Mức lương cơ bản là 9.000.000 đồng/tháng, trả vào ngày 05 hàng tháng qua chuyển khoản.",
         ["COMPENSATION_BENEFITS"]),
        ("Điều 4", "Chấm dứt hợp đồng",
         "Mỗi bên có quyền đơn phương chấm dứt hợp đồng lao động nếu báo trước ít nhất 30 ngày bằng văn bản.",
         ["TERMINATION"]),
    ],
    "SYN-HD-003": [
        ("Điều 1", "Vị trí công việc",
         "Người lao động đảm nhận vị trí Lập trình viên Backend, chịu trách nhiệm phát triển hệ thống nội bộ.",
         ["JOB_INFO"]),
        ("Điều 2", "Bảo mật thông tin và không cạnh tranh",
         "Người lao động cam kết không tiết lộ mã nguồn, tài liệu kỹ thuật cho bên thứ ba trong và sau thời gian làm việc.",
         ["EMPLOYEE_OBLIGATIONS_DISCIPLINE"]),
        ("Điều 3", "Chấm dứt hợp đồng trước hạn",
         "Trường hợp chấm dứt hợp đồng trước hạn, người lao động phải bàn giao toàn bộ mã nguồn, tài khoản hệ thống và không được làm việc cho đối thủ cạnh tranh trực tiếp trong vòng 12 tháng kể từ ngày nghỉ việc.",
         ["EMPLOYEE_OBLIGATIONS_DISCIPLINE", "TERMINATION"]),
        ("Điều 4", "Bảo hiểm và phúc lợi",
         "Công ty đóng bảo hiểm xã hội, bảo hiểm y tế, bảo hiểm thất nghiệp đầy đủ theo quy định pháp luật.",
         ["INSURANCE_SAFETY"]),
        ("Điều 5", "Giải quyết tranh chấp",
         "Mọi tranh chấp phát sinh được ưu tiên giải quyết thông qua thương lượng; nếu không thành, đưa ra Tòa án nhân dân có thẩm quyền.",
         ["OTHER"]),
    ],
    "SYN-HD-004": [
        ("Điều 1", "Công việc",
         "Người lao động đảm nhận vị trí Nhân viên kinh doanh, phụ trách khu vực miền Bắc.",
         ["JOB_INFO"]),
        ("Điều 2", "Lương và hoa hồng",
         "Lương cứng 6.000.000 đồng/tháng cộng hoa hồng 5% trên doanh số bán hàng thực tế đạt được trong tháng.",
         ["COMPENSATION_BENEFITS"]),
        ("Điều 3", "Bảo hiểm xã hội",
         "Công ty thực hiện đóng bảo hiểm xã hội bắt buộc cho người lao động kể từ tháng làm việc thứ hai.",
         ["INSURANCE_SAFETY"]),
        ("Điều 4", "Giải quyết tranh chấp",
         "Hai bên cam kết giải quyết tranh chấp trên tinh thần hợp tác; trường hợp cần thiết sẽ đề nghị hòa giải viên lao động hỗ trợ.",
         ["OTHER"]),
        ("Điều 5", "Điều khoản chung",
         "Hợp đồng này có hiệu lực kể từ ngày ký, được lập thành 02 bản, mỗi bên giữ 01 bản có giá trị pháp lý như nhau.",
         ["OTHER"]),
    ],
    "SYN-HD-005": [
        ("Điều 1", "Công việc và địa điểm",
         "Người lao động đảm nhận vị trí Công nhân vận hành máy tại Nhà máy số 2 của công ty.",
         ["JOB_INFO"]),
        ("Điều 2", "Thời giờ làm việc theo ca",
         "Người lao động làm việc theo ca luân phiên (ca ngày, ca đêm), mỗi ca 8 giờ, được nghỉ giữa ca 30 phút.",
         ["WORKING_TIME"]),
        ("Điều 3", "Thử việc và chấm dứt hợp đồng",
         "Thời gian thử việc là 30 ngày; trong thời gian thử việc, mỗi bên có quyền chấm dứt việc thực hiện hợp đồng mà không cần báo trước.",
         ["TERMINATION"]),
        ("Điều 4", "Tiền lương làm thêm giờ",
         "Người lao động làm thêm giờ được trả lương bằng 150% vào ngày thường, 200% vào ngày nghỉ hằng tuần.",
         ["COMPENSATION_BENEFITS"]),
    ],
    "SYN-HD-006": [
        ("Điều 1", "Chức danh và nhiệm vụ",
         "Người lao động đảm nhận vị trí Trưởng phòng Marketing, quản lý trực tiếp đội ngũ 5 nhân viên.",
         ["JOB_INFO"]),
        ("Điều 2", "Lương, thưởng KPI",
         "Lương cơ bản 20.000.000 đồng/tháng; thưởng hiệu suất (KPI) được tính theo quý dựa trên kết quả kinh doanh của phòng.",
         ["COMPENSATION_BENEFITS"]),
        ("Điều 3", "Bảo mật thông tin và sở hữu trí tuệ",
         "Mọi chiến lược kinh doanh, dữ liệu khách hàng và tài liệu nội bộ đều thuộc quyền sở hữu của công ty; người lao động không được sao chép, chuyển giao cho bất kỳ bên thứ ba nào.",
         ["EMPLOYEE_OBLIGATIONS_DISCIPLINE"]),
        ("Điều 4", "Giải quyết tranh chấp bằng trọng tài",
         "Mọi tranh chấp phát sinh từ hợp đồng này sẽ được giải quyết tại Trung tâm Trọng tài Quốc tế Việt Nam (VIAC) theo quy tắc tố tụng trọng tài hiện hành.",
         ["OTHER"]),
        ("Điều 5", "Điều khoản thi hành",
         "Hợp đồng có hiệu lực kể từ ngày hai bên ký tên, mọi sửa đổi bổ sung phải được lập thành văn bản.",
         ["OTHER"]),
    ],
    "SYN-HD-007": [
        ("Điều 1", "Công việc thời vụ",
         "Người lao động đảm nhận công việc đóng gói sản phẩm theo thời vụ tại xưởng sản xuất.",
         ["JOB_INFO"]),
        ("Điều 2", "Thời giờ làm việc, nghỉ ngơi và phúc lợi",
         "Người lao động làm việc không quá 8 giờ/ngày và 48 giờ/tuần, được nghỉ ít nhất 1 ngày/tuần, đồng thời được công ty hỗ trợ bữa ăn ca và bố trí xe đưa đón trong suốt thời gian hợp đồng thời vụ.",
         ["WORKING_TIME", "LEAVE", "COMPENSATION_BENEFITS"]),
        ("Điều 3", "Chấm dứt hợp đồng thời vụ",
         "Hợp đồng tự động chấm dứt khi hết thời hạn thời vụ đã thỏa thuận mà không cần thông báo trước.",
         ["TERMINATION"]),
        ("Điều 4", "Hiệu lực hợp đồng",
         "Hợp đồng được lập thành 02 bản bằng tiếng Việt, có hiệu lực kể từ ngày ký.",
         ["OTHER"]),
    ],
}


def build_contract(contract_id: str, blocks: list[tuple[str, str, str, list[str]]]) -> dict:
    block_texts = [f"{number}. {title}\n{content}" for number, title, content, _ in blocks]
    raw_text = HEADER + "\n".join(block_texts)

    gold_clauses = []
    cursor = 0
    for i, (block_text, (_, _, _, labels)) in enumerate(zip(block_texts, blocks)):
        idx = raw_text.find(block_text, cursor)
        if idx == -1:
            raise ValueError(f"[{contract_id}] Không tìm thấy block #{i} trong raw_text — kiểm tra lại nội dung.")
        start, end = idx, idx + len(block_text)
        # Kiểm tra bất biến quan trọng nhất: slice lại đúng y hệt text gốc.
        assert raw_text[start:end] == block_text, f"[{contract_id}] Offset lệch ở block #{i}!"
        gold_clauses.append(
            {
                "clause_id": f"c{i + 1}",
                "start_offset": start,
                "end_offset": end,
                "label": labels,
            }
        )
        cursor = end

    return {"contract_id": contract_id, "raw_text": raw_text, "gold_clauses": gold_clauses}


def main():
    dataset = [build_contract(cid, blocks) for cid, blocks in CONTRACTS.items()]

    total_clauses = sum(len(c["gold_clauses"]) for c in dataset)
    label_counts: dict[str, int] = {}
    for c in dataset:
        for gc in c["gold_clauses"]:
            for label in gc["label"]:
                label_counts[label] = label_counts.get(label, 0) + 1

    out_path = Path(__file__).parent / "synthetic_v0.2.json"
    out_path.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ Đã ghi {out_path} — {len(dataset)} hợp đồng, {total_clauses} clause.")
    print("Phân bố nhãn:")
    for label, count in sorted(label_counts.items(), key=lambda x: -x[1]):
        print(f"  {label}: {count}")


if __name__ == "__main__":
    main()