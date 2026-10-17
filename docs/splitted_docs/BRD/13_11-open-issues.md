<!-- nguồn: BRD_AI_Labor_Contract_Risk_Analyzer_0_5.md | mục: BRD: AI Labor Contract Risk Analyzer > 11. Open Issues | 2899 ký tự | trước: 12_phu-luc-b-thuat-ngu.md | sau: 14_phu-luc-c-cho-codebase-hien-tai-lech-brd-ghi-nhan.md -->

## 11. Open Issues

Mục chưa chốt. Mỗi mục có người chịu trách nhiệm, hạn và giá trị tạm dùng cho đến khi chốt.

| ID | Vấn đề | Chịu trách nhiệm | Giá trị tạm dùng |
|---|---|---|---|
| OI-01 | Risk taxonomy chưa tồn tại (clause taxonomy 12 nhãn đã có) | Chưa phân công | Dựng bản đầu từ các quy định dùng cho lỗi chèn |
| OI-02 | Danh mục kho luật tầng 1 và các Điều dùng cho lỗi chèn | Người phụ trách dữ liệu | Bộ luật Lao động 2019 và nghị định hướng dẫn |
| OI-03 | Xác nhận văn bản hiện hành về bảo vệ dữ liệu cá nhân (kể cả gửi ra nhà cung cấp ở nước ngoài) và chính sách lưu, sử dụng dữ liệu của Gemini Paid Tier | Chưa phân công | Thông báo không cam kết tuyệt đối (Phụ lục A) |
| OI-04 | Phân công các mảng chưa có chủ (§9.6) | Cả nhóm | Chưa có |
| OI-05 | Xác nhận MS-2 đến MS-5 (§9.4) | Cả nhóm | Lịch đề xuất ở §9.4 |
| OI-06 | Hành vi khi hệ thống đang xử lý một phiên khác | Cả nhóm | Từ chối phiên mới kèm thông báo thử lại sau |
| OI-07 | Chọn LLM thông dụng làm baseline cho BL-1 | Cả nhóm | Chưa chọn; BL-1 là hạng mục cắt đầu tiên |
| OI-08 | Nghị định xử phạt vi phạm hành chính về lao động hiện hành tại ngày phân tích. Tra cứu ngày 12/10/2026 cho thấy có quy định xử phạt thay đổi từ 10/9/2026, chưa kiểm chứng | Người phụ trách dữ liệu | Báo cáo không nêu mức phạt |
| OI-09 | Đặt lại ngưỡng M2, M7, M3b sau số đo dev đầu tiên | Cả nhóm | 0.80, 0.80, 85% |
| OI-10 | Số hợp đồng của T1 và số lỗi chèn của T2 có thể đổi | Cả nhóm | Xem lại ngưỡng và cỡ mẫu (§8.2) |
| OI-11 | Chọn model Claude cụ thể làm judge và phần ngân sách | Cả nhóm | Một model Claude, chi phí trong \$15 |
| OI-12 | Mô hình chi phí; trần số điều khoản; ngưỡng ký tự DOCX theo số đo trên D1 | Cả nhóm | 150 điều khoản; 100.000 ký tự |
| OI-13 | Refine pipeline: xem SRS OI-01 | Cả nhóm | Pipeline ở SRS 2.2; mọi thay đổi giữ các invariant |
| OI-14 | Đã chốt 12/10/2026: Data Graph phục vụ Retrieval & Fact-finding; Clause Graph phục vụ Validation & Reasoning (kiểm tra mâu thuẫn, suy diễn điều kiện). Còn mở: thiết kế cụ thể cách Clause Graph dùng cho kiểm tra mâu thuẫn và suy diễn điều kiện (xem OI-17) | Cả nhóm | Clause Graph có cạnh cấu trúc (SRS FR-31); chưa gắn tính năng người dùng cho đến khi SDD và TDD quyết định |
| OI-15 | Đã chốt 12/10/2026: 10 tuần là 8 tuần xây dựng đến demo cộng 2 tuần đánh giá. Còn chờ xác nhận: các mốc MS-2, MS-4, MS-5 (9.4, cũng là OI-05) | Cả nhóm | Lịch ở 9.4 |
| OI-16 | Chính sách đa nhãn: dữ liệu gold hiện một nhãn mỗi dòng, quy tắc 6 ở 8.2 cho phép nhiều nhãn (SRS OI-10) | Người phụ trách dữ liệu, Clause AI | Mỗi clause 1 đến 3 nhãn; hướng dẫn gán: ưu tiên một nhãn, thêm nhãn khi câu không tách được |
| OI-17 | Thiết kế Graph ở mức SDD và TDD (loại nút và cạnh, nguồn cạnh, số bước mở rộng; SRS OI-08, OI-09) | Cả nhóm | Theo SRS FR-30, FR-31 |
| OI-18 | Duyệt thay đổi BRD 0.5 và SRS 1.3, gồm các điều ở Phụ lục C | Chủ sở hữu BRD, SRS | Chờ duyệt |
