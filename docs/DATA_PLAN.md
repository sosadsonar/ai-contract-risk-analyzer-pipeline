# Data Plan v1 — Contract Risk Analyzer

Owner: Người 1 – Clause AI Lead (dùng chung cho cả nhóm vì dataset phục vụ cả Clause Detection lẫn Risk Classification)
Trạng thái: chốt Tuần 1, cập nhật số liệu thật mỗi tuần trong Weekly Note.

## 1. Mục tiêu dataset

Dataset dùng để: (a) đo Clause Detection F1 (span-level, xem `eval/eval_segmentation.py`), (b) đo Risk Classification Macro-F1, (c) làm few-shot examples cho prompt engineering. Không dùng để fine-tune model (dự án dùng LLM có sẵn qua prompt, không train từ đầu), nên không cần tập train lớn — quan trọng là tập **dev/gold** đủ đa dạng và được gán nhãn chính xác.

## 2. Nguồn dữ liệu

- **Nguồn chính (Tuần 1–3): hợp đồng lao động tổng hợp/tự soạn** dựa trên cấu trúc phổ biến của hợp đồng lao động tại Việt Nam (không copy nguyên văn từ một hợp đồng thật cụ thể nào để tránh vấn đề bản quyền/riêng tư). Ưu điểm: kiểm soát được việc phủ đủ mọi nhãn trong taxonomy ngay từ đầu, không lo lộ thông tin cá nhân.
- **Nguồn bổ sung (Tuần 4 trở đi, nếu có):** hợp đồng thật do thành viên nhóm/người quen tự nguyện cung cấp, **bắt buộc ẩn danh hóa** (xóa tên, MSNV, số CMND/CCCD, số điện thoại, mức lương cụ thể nếu người cung cấp yêu cầu) trước khi đưa vào repo. File hợp đồng thô (`data/raw/`, `*.pdf`, `*.docx`) đã được thêm vào `.gitignore` — không commit file gốc, chỉ commit bản đã trích xuất/ẩn danh dưới dạng JSON.
- Nếu đến Tuần 4 không xin được hợp đồng thật nào, ghi rõ trong Weekly Note và tiếp tục mở rộng bằng dữ liệu tổng hợp có kiểm soát độ khó (câu dài, nhiều mệnh đề, hành văn không chuẩn hoá do OCR) để mô phỏng dữ liệu thật.

## 3. Khối lượng mục tiêu theo tuần

| Mốc | Số hợp đồng | Số clause ước tính | Mục đích |
|---|---|---|---|
| Tuần 1 (hiện tại) | 6 (`golden_v0.2.json`) | ~28 | Validate schema, chạy thử eval script, có đủ ví dụ cho mỗi nhãn trong taxonomy |
| Tuần 3 | 15–20 | ~80–100 | Baseline F1 đầu tiên có ý nghĩa thống kê (không còn quá ít mẫu) |
| Tuần 5 | 30+ | ~150–200 | Đạt mức đủ để báo cáo Clause Detection F1 ≥0.85 / Macro-F1 ≥0.80 đáng tin cậy |
| Tuần 8 | 40–50 | ~200–250 | Tập test cuối để freeze, để dành ~20% không đụng tới cho benchmark cuối kỳ (Tuần 9) |

Lưu ý: từ Tuần 5, cần tách rõ **dev set** (dùng để tinh chỉnh prompt/threshold, được phép nhìn nhiều lần) và **test set giữ kín** (chỉ chạy 1–2 lần, dùng cho benchmark Tuần 9) để tránh overfit lên prompt.

## 4. Quy trình gán nhãn (Annotation Guideline — draft)

1. Đọc toàn bộ hợp đồng trước khi cắt clause, xác định các "Điều" theo đánh số gốc.
2. Với mỗi Điều, nếu bên trong có nhiều ý khác nhóm nhãn rõ rệt (ví dụ vừa mô tả công việc vừa có điều khoản bảo mật), có thể **cắt thành nhiều clause con** thay vì gán đa nhãn cho cả khối lớn — chỉ đa nhãn khi hai ý thực sự nằm trong cùng một câu/đoạn không tách được.
3. `start_offset`/`end_offset` tính theo ký tự (character index) trên `raw_text` gốc, lấy chính xác theo `str.find`/slicing, không làm tròn theo dòng.
4. Nhãn áp dụng theo bảng ở `docs/CLAUSE_TAXONOMY.md`. Khi phân vân, tuân theo mục "Quy tắc gán nhãn khi mơ hồ" trong tài liệu đó.
5. Mỗi hợp đồng tổng hợp mới nên có ít nhất 1 clause "khó" có chủ đích (câu dài nhiều mệnh đề, hoặc điều khoản đa nhãn) để dataset không chỉ toàn câu dễ.
6. Người gán nhãn: hiện tại do Clause AI Lead tự làm ở Tuần 1 (vì dữ liệu tổng hợp); khi có hợp đồng thật, cần ít nhất 1 người review chéo (double-annotation) trên một tập con nhỏ để tính độ đồng thuận liên-annotator, phục vụ chỉ số "Human Agreement" của cả dự án.

## 5. Versioning dữ liệu

- `golden_v0.1.json` — bản pilot Tuần 1 ban đầu, 1 hợp đồng / 2 clause, dùng để validate schema JSON. **Giữ nguyên, không xóa**, để có lịch sử.
- `golden_v0.2.json` — mở rộng Tuần 1 (bản này), 6 hợp đồng tổng hợp / ~28 clause, phủ đủ 8 nhãn trong taxonomy v1, có sinh bằng script `data/build_golden_v0_2.py` để đảm bảo offset chính xác tuyệt đối (không gõ tay số ký tự, tránh lỗi lệch span).
- Từ Tuần 3 trở đi: đặt tên `golden_v0.3.json`, `v0.4.json`... mỗi lần tăng đáng kể về số lượng hoặc đổi taxonomy. Không sửa đè lên version cũ.

## 6. Rủi ro / giới hạn đã biết (ghi lại để không bị hỏi bất ngờ)

- Dữ liệu Tuần 1–3 là **tổng hợp (synthetic)**, không phải hợp đồng thật 100% → có thể sạch/chuẩn hơn thực tế (câu văn rõ ràng, đánh số Điều nhất quán). F1 đo trên tập này có thể cao hơn khi chạy trên hợp đồng thật/scan OCR — cần nêu rõ giới hạn này trong báo cáo cuối kỳ, không nhận vơ là số liệu trên dữ liệu thật.
- `document_router` (ngưỡng match_ratio 0.40 trong `utils/text_processing.py`) và các ngưỡng `t_low/t_high` trong `thresholds.py` hiện là **giả định ban đầu**, chưa được tinh chỉnh bằng thực nghiệm — sẽ hiệu chỉnh sau khi có kết quả trên `golden_v0.2.json` trở lên.

## 7. Việc cần làm tiếp (sau Tuần 1)

- Chạy `eval_segmentation.py` trên `golden_v0.2.json` để có F1 baseline đầu tiên (dù dùng LLM hay rule-based).
- Xin ý kiến 1 thành viên khác trong nhóm đọc thử `docs/CLAUSE_TAXONOMY.md` để phát hiện nhãn/định nghĩa còn mơ hồ trước khi mở rộng dataset ở Tuần 3.
