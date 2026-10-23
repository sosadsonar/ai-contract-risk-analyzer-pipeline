<!-- nguồn: SRS_AI_Labor_Contract_Risk_Analyzer_1_4.md | mục: SRS: AI Labor Contract Risk Analyzer (phiên bản 1.4) > 2. Mô tả tổng quan và quyết định thiết kế | 3051 ký tự | trước: 02_1-gioi-thieu.md | sau: 04_3-yeu-cau-chuc-nang-phan-1-2.md -->

## 2. Mô tả tổng quan và quyết định thiết kế

### 2.1 Actors

| Actor | Vai trò | Nghiệp vụ |
|---|---|---|
| Người lao động (NLĐ) | Người dùng cuối | Phân tích các điều khoản hiện có theo góc nhìn NLĐ. |
| Người sử dụng lao động (NSDLĐ) | Người dùng cuối | Phân tích các điều khoản hiện có theo góc nhìn NSDLĐ. |
| Người phụ trách dữ liệu | Thành viên nhóm phát triển | Duy trì kho luật, metadata hiệu lực, các taxonomy và guideline liên quan. |

### 2.2 Pipeline bắt buộc

Sơ đồ dưới là pipeline của sản phẩm. Các quy tắc sau áp dụng cho mọi thiết kế chi tiết ở SDD và TDD (pipeline có thể được refine ở SDD, xem OI-01, miễn không đổi các quy tắc này):

[Hình: pipeline sản phẩm · 10 bước, 2 bước gọi LLM]

pipeline sản phẩm · 10 bước, 2 bước gọi LLM

Hai bước tô màu là các lần gọi LLM bên thứ ba; các bước còn lại chạy trong hệ thống của nhóm.

* LLM bên thứ ba không được nhận canonical text chưa che.
* LLM không được tạo hoặc chỉnh start_char, end_char và không được tạo quote để highlight.
* Mọi output AI downstream phải tham chiếu clause_id; backend là nơi ghép kết quả với original_text và span từ canonical text.
* Invariant: canonical_text[start_char:end_char] == original_text; len(masked_text) == len(canonical_text); masked_text[start_char:end_char] là clause đã che.
* Sản phẩm có hai bước LLM bắt buộc: Clause Classification, và Risk + Explanation + chọn citation (severity do backend tra bảng taxonomy). Bước LLM hỗ trợ tách điều khoản là tùy chọn (hạng mục cắt số 3). Judge chạy ngoại tuyến, không thuộc pipeline sản phẩm.
* Legal Retrieval chạy cục bộ, không gọi LLM.
* Legal Retrieval gồm retrieval nền và bước mở rộng qua Data Graph (FR-12, FR-30). Tắt bước mở rộng thì hệ thống vẫn chạy đúng.
* Clause Graph được dựng cục bộ ngay sau Segmentation, không gọi LLM và không thêm bước LLM (FR-31). Context Resolver lấy các clause liên quan từ graph và chỉ gửi masked related context vào Risk LLM; output vẫn gắn target clause_id. Sơ đồ trên chưa vẽ Graph vì đây là chi tiết local đã được refine ở SDD/TDD.

### 2.3 Taxonomy và severity

* Clause taxonomy (12 nhãn) nằm ở /data/docs/clause_taxonomy. Risk taxonomy chưa có; placeholder đặt cùng thư mục tại /data/docs/risk_taxonomy. Hai artifact tách biệt, có phiên bản, và được đóng băng cùng severity rubric và annotation guideline ở MS-1 (25/10/2026) theo DEC-10.
* Severity: HIGH, MEDIUM, LOW. Severity có thể khác nhau giữa hai vai trò và là null khi evidence_status = INSUFFICIENT_EVIDENCE.
* Điều khoản có lợi hơn mức pháp luật yêu cầu cho một vai trò không phải rủi ro của vai trò đó (BRD 3.2).

| Severity | Rubric tối thiểu (theo vai trò đang phân tích) |
|---|---|
| HIGH | Điều khoản trực tiếp xung đột quy định cấm hoặc bắt buộc, hoặc vượt ngưỡng pháp luật rõ ràng trong kho luật; hoặc tạo nguy cơ mất quyền hay nghĩa vụ trái luật đáng kể. |
| MEDIUM | Điều khoản có dấu hiệu bất lợi đáng kể, mơ hồ hoặc có khả năng dẫn đến tranh chấp nhưng không thỏa điều kiện HIGH theo căn cứ hiện có. |
| LOW | Vấn đề mức độ nhẹ, câu chữ chưa rõ hoặc bất lợi hạn chế; tác động pháp lý thấp theo căn cứ hiện có. |
