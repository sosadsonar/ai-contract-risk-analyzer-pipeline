<!-- nguồn: DATA_LEAD_REVIEW_V03.md | mục: Data Lead review cho PR #2 — 12/10/2026 > Audit 9 unmatched span | 2275 ký tự | trước: 02_doi-chieu-taxonomy.md | sau: 04_tien-do-tuan-5-so-voi-ke-hoach-goc.md -->

## Audit 9 unmatched span

Số "7 context + 1 C027" trong PR gốc chưa đủ 9. Ca còn lại là C014 khác
ký tự nguồn, không phải context duplication.

| Clause ID | Nhãn hiện có | Nguyên nhân / bằng chứng | Quyết định source span |
|---|---|---|---|
| HDLD001_C014 | WORKING_TIME | Nguồn có `hàng tuầnS`; annotation không có `S` và tiền tố bullet | CONTEXT; không sửa nguồn/annotation |
| HDLD003_C018 | INSURANCE_SAFETY | Tách bảo hiểm từ bullet đóng bảo hiểm và thuế; highlight `các loại bảo hiểm` | CONTEXT |
| HDLD003_C018A | EMPLOYEE_OBLIGATIONS_DISCIPLINE | Cùng bullet; highlight `các khoản thuế`, lặp ngữ cảnh nghĩa vụ đóng | CONTEXT |
| HDLD004_C023 | LEAVE | Tách nghỉ ngơi khỏi bullet nghỉ/học nghề; lặp ngữ cảnh chung | CONTEXT |
| HDLD004_C024 | TRAINING | Tách học nghề-văn hóa từ cùng bullet | CONTEXT |
| HDLD004_C025 | WORKING_CONDITIONS | Tách chỗ ăn/ở từ bullet đa chủ đề | CONTEXT |
| HDLD004_C026 | INSURANCE_SAFETY | Tách bảo hộ lao động từ cùng bullet | CONTEXT |
| HDLD004_C027 | OTHER | Quyền chung NLĐ về bồi thường; source có cụm `bồi thường thiệt hại` và chỗ trống để thỏa thuận | CONTEXT; giữ OTHER theo v0.3 §4.6 |
| HDLD004_C043 | CONTRACT_TERM | Tách ngày hiệu lực, lặp chủ ngữ `Hợp đồng này` từ câu số bản/hiệu lực | CONTEXT |

C027 có nội dung nguồn; không phải row trống hoặc nhãn pháp lý đã được xác
nhận. Không bịa mức/điều kiện bồi thường vào chỗ trống. Audit chỉ xác nhận
source reference, offset và căn cứ taxonomy đang dùng; legal-risk gold là null.

Kết quả script: 234 clause, 225 EXACT đã kiểm khớp sau gom khoảng trắng,
9 CONTEXT có source reference khớp anchor/phrase đã review trong script
`data/scripts/build_context_offsets.py` của commit được pin. Script audit tái
dựng các anchor từ v04 và so sánh offset v06; đoạn không rỗng nhưng không liên
quan bị từ chối. Giữ nguyên nội dung/nhãn của 183
annotation lịch sử khi đối chiếu v04 với v06; raw/data submodule không bị sửa.
7 ca context reuse + 1 C027 taxonomy gap + 1 source text difference = 9.

Đơn vị offset là Unicode code point, `[start,end)` trên đúng raw text đã hash.
CONTEXT phải giữ `span=null`/không chấm exact gold ở consumer; có thể dùng
source-reference span riêng cho highlight. Không ép `_locate_span` tìm một
đoạn nguyên văn giả cho câu annotation đã lặp ngữ cảnh.
