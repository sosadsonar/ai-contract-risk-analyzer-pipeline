<!-- nguồn: BRD_AI_Labor_Contract_Risk_Analyzer_v0.6.md | mục: BRD: AI Labor Contract Risk Analyzer | 3271 ký tự | trước: - | sau: 01_1-tong-quan.md -->

# BRD: AI Labor Contract Risk Analyzer

*Phiên bản 0.6 (dự thảo, chờ duyệt) | 03/11/2026*

Thay đổi chính trong 0.6 so với 0.5 (audit tài liệu ngày 03/11/2026):

- 3.2: định nghĩa ba loại căn cứ theo vai trò (UNFAVORABLE có dấu hiệu N1 đến N3 và E1 đến E3), LEGAL_VIOLATION tách khỏi UNFAVORABLE, AMBIGUOUS gồm thiếu số liệu và mâu thuẫn giữa hai điều khoản; mọi loại căn cứ đều được kỳ vọng có citation (BR-07, BR-08, BR-15); bỏ tham chiếu sai tới 8.2.
- 3.3: viết lại thành sáu điều khoản mẫu theo risk taxonomy (sửa ca 4, thêm ca 6).
- 2.1, 4.1, 7.1: dùng canonical text; 4.1 bỏ tên model.
- 5: BR-07, BR-08, BR-15 và BR-18 (Clause Graph phát hiện mâu thuẫn qua related_clause_ids; suy diễn điều kiện chưa có tiêu chí nghiệm thu).
- 7.2, 7.3: danh sách che và giữ cập nhật; bỏ "địa bàn làm việc cấp tỉnh"; vùng lương tối thiểu kiểm theo cận dưới vùng IV (OI-19).
- 8.2, 8.3, 8.6: D1 theo clauses_v06, thêm D3 và P1; thêm M2b, M9, M10 và quy tắc quy đổi gold sang đầu ra pipeline; nghiệm thu M1 đến M10 và BR-01 đến BR-18; sáu ca mẫu.
- 9.4, 11: ghi nhận MS-1 trễ; cập nhật OI-01 và OI-18; thêm OI-19.

Thay đổi chính trong 0.5 so với 0.4:

- 1, 2.1, 3.1: thêm Data Graph (Retrieval & Fact-finding) và Clause Graph (Validation & Reasoning) theo yêu cầu của giảng viên (BO-5, BR-17, BR-18); BO-4 bỏ chữ "đều" như đã ghi ở 0.4.
- 5: bảng BR nay có BR-05a, BR-05b, BR-05c và BR-16 (đã ghi ở 0.4 nhưng chưa có trong bảng); thêm BR-17, BR-18.
- 7: đánh số 7.1 đến 7.6; thêm 7.3 ngưỡng ẩn dữ liệu cá nhân (chuyển từ SRS NFR-SEC-01); 7.5 gồm cả judge; 7.6 dữ liệu dev và test; thêm quy định không lưu nội dung hợp đồng ở kho bền vững.
- 8: M1 ghi rõ cách khớp IoU; M8 báo thêm có và không dùng Graph; sửa hai câu cụt (BL-1, 8.5).
- 9: 9.1 làm rõ 10 tuần là 8 tuần xây dựng cộng 2 tuần đánh giá; thêm 9.4 Mốc thời gian, đổi Thứ tự cắt thành 9.5, thêm 9.6 Phân công (khớp các tham chiếu §9.4, §9.5, §9.6 đã có sẵn trong BRD 0.4); thêm hạng mục cắt số 5 cho Graph.
- 10: thêm rủi ro về Graph và về codebase lệch tài liệu. 11: thêm OI-14 đến OI-18.
- Phụ lục B thêm thuật ngữ Graph; thêm Phụ lục C ghi nhận chỗ codebase hiện tại lệch BRD (chưa sửa code; chi tiết kỹ thuật ở SRS Phụ lục C).

Thay đổi chính trong 0.4 so với 0.3:

- 1: BO-1 đổi từ 10 tuần sang 8 tuần, BO-2 và BO-4 viết lại theo cách đo được; bảng chỉ số thành công chỉ dẫn ID ở §8, không lặp số.
- 3: thêm định nghĩa "rủi ro" và 5 điều khoản mẫu theo vai trò.
- 4.1: bước 5 đổi thành che dữ liệu cá nhân trước, tách điều khoản sau; bỏ tên model và tên thuật toán khỏi luồng người dùng.
- 4.2 và 6: thêm ca từ chối khi hệ thống bận, khi vượt trần điều khoản hoặc trần chi phí; file bị từ chối kết thúc phiên.
- 5: tách BR-05 thành BR-05a, BR-05b, BR-05c; BR-09 đổi sang highlight trên văn bản trích xuất; BR-10 bổ sung cảnh báo không kiểm tra điều khoản thiếu; thêm BR-16 (trần chi phí).
- 7: ngưỡng PII theo loại, bỏ chữ "đều" ở BO-4, thông báo dữ liệu nói rõ nhà cung cấp LLM có chính sách lưu riêng.
- 8: viết lại thành Evaluation Plan nằm trong BRD: bốn tập dữ liệu (T1, T2, D1, D2), chỉ số M1 đến M8 (M3 tách thành M3a và M3b, thêm M7 và M8) và BL-1, giao thức judge dùng Claude, tiêu chí nghiệm thu.
- 9: ngân sách \$20, mốc thời gian, phân công, thứ tự cắt bỏ tính năng (nếu quá deadline).
- 11: Open Issues.
