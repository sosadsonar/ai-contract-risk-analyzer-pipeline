<!-- nguồn: BRD_AI_Labor_Contract_Risk_Analyzer_0_5.md | mục: BRD: AI Labor Contract Risk Analyzer > Phụ lục C: Chỗ codebase hiện tại lệch BRD (ghi nhận, chưa sửa code) | 1697 ký tự | trước: 13_11-open-issues.md | sau: - -->

## Phụ lục C: Chỗ codebase hiện tại lệch BRD (ghi nhận, chưa sửa code)

Đối chiếu ngày 12/10/2026 với snapshot ai_pipeline, backend, docs. Snapshot không có frontend nên phần giao diện chưa đối chiếu được. Danh sách thay đổi kỹ thuật chi tiết nằm ở SRS Phụ lục C.

| Hạng mục | Codebase hiện tại | BRD yêu cầu | Xử lý đã ghi nhận |
|---|---|---|---|
| Nhà cung cấp LLM | Gemini free tier và Qwen qua Ollama; model mặc định ngầm | Gemini Flash gói trả phí, không tự host (7.5, 9.1) | Gói miễn phí và Qwen chỉ dùng dev với dữ liệu de-identify; demo và đánh giá dùng gói trả phí |
| Lưu trữ | PostgreSQL lưu nội dung hợp đồng lâu dài | BR-13: xóa khi hết phiên | Không lưu nội dung hợp đồng ở kho bền vững (7.4; SRS NFR-DATA-04) |
| Định dạng nhận | Chỉ PDF | PDF và DOCX (BR-02) | Bổ sung DOCX |
| Nhãn và độ tin cậy | Điểm tự tin, tier theo nhãn, review_zone; dữ liệu gold một nhãn mỗi dòng | Nhãn clause theo taxonomy; quy tắc 6 ở 8.2 | Bỏ điểm, tier, review_zone; chốt chính sách đa nhãn (OI-16) |
| Tách điều khoản | LLM đọc văn bản chưa che, tự trả nguyên văn, hệ thống dò lại vị trí | BR-04, BR-05a, BR-05b: che trước, hệ thống tự tính vị trí | Tách bằng luật cấu trúc, LLM chỉ phân loại theo mã điều khoản |
| Kế hoạch dữ liệu | DATA_PLAN: dữ liệu tổng hợp, 8 nhãn, 40 đến 50 hợp đồng | 8.2: D1, D2, T1, T2 với hợp đồng thật de-identify | DATA_PLAN lỗi thời; thay bằng con trỏ về 8.2, giữ annotation guideline |
| Nguồn nhãn clause | Bốn bản (repo dữ liệu, taxonomy.py, docs, enum schema) | Taxonomy đóng băng ở MS-1 (8.2, quy tắc 5) | Một nguồn duy nhất trong code; enum schema sinh từ đó hoặc có test đối chiếu |
| Graph | Chưa có | BR-17, BR-18 | Thêm vào kế hoạch; thiết kế ở SDD và TDD |
