<!-- nguồn: SRS_AI_Labor_Contract_Risk_Analyzer_1_4.md | mục: SRS: AI Labor Contract Risk Analyzer (phiên bản 1.4) > 1. Giới thiệu | 3902 ký tự | trước: 01_kiem-soat-tai-lieu.md | sau: 03_2-mo-ta-tong-quan-va-quyet-dinh-thiet-ke.md -->

## 1. Giới thiệu

### 1.1 Mục đích tài liệu

Tài liệu đặc tả yêu cầu phần mềm của AI Labor Contract Risk Analyzer ở mức đủ để làm căn cứ cho thiết kế hệ thống (SDD), thiết kế kỹ thuật (TDD), triển khai, chia việc và kiểm thử. Input là BRD 0.5. Ngưỡng và cách đo mọi chỉ số chất lượng nằm ở BRD 8; SRS chỉ dẫn ID.

### 1.2 Phạm vi sản phẩm

* Web app cho máy tính, giao diện tiếng Việt, không yêu cầu đăng ký tài khoản.

* Mỗi phiên gắn với đúng một vai trò (NLĐ hoặc NSDLĐ) và một hợp đồng.

* Đầu vào: HĐLĐ tiếng Việt dạng PDF hoặc DOCX có sẵn text, đã soạn đầy đủ điều khoản và chưa ký.

* Hệ thống chỉ phân tích rủi ro phát sinh từ các điều khoản thực sự có trong hợp đồng.

* Kết quả gồm điều khoản rủi ro, risk label, severity HIGH, MEDIUM hoặc LOW, giải thích, căn cứ luật và highlight trên canonical text.

* Data Graph (đồ thị kho luật, phục vụ Retrieval & Fact-finding) và Clause Graph (đồ thị điều khoản của hợp đồng trong phiên, phục vụ Validation & Reasoning), theo yêu cầu của giảng viên (DEC-21).

* Kết quả chỉ mang tính tham khảo, không phải tư vấn pháp lý.

### 1.3 Ngoài phạm vi

* Phát hiện rủi ro do thiếu hoàn toàn một điều khoản bắt buộc (missing-clause risk).

* Chatbot hoặc hỏi đáp sau khi có kết quả.

* Lời khuyên pháp lý, gợi ý sửa điều khoản hoặc đề xuất thương lượng.

* PDF scan, ảnh chụp, OCR; hợp đồng không phải tiếng Việt.

* Highlight đè trực tiếp lên PDF hoặc DOCX gốc (DEC-04).

* Xử lý nhiều phiên song song (DEC-05).

* Tài khoản người dùng, lịch sử lâu dài, thanh toán, mobile app, giao diện tiếng Anh.

* Tự huấn luyện, fine-tune hoặc self-host mô hình.

* Yêu cầu quy mô hay độ ổn định production.

### 1.4 Thuật ngữ

| Thuật ngữ | Ý nghĩa |
|---|---|
| Phiên | Một lần làm việc với một vai trò và một hợp đồng, định danh bằng session_id (BRD Phụ lục B). |
| Canonical text | Chuỗi văn bản chuẩn duy nhất sinh từ tài liệu, Unicode NFC; dùng cho tách điều khoản, span, lưu trữ, highlight và export. |
| Masked text | Bản của canonical text sau khi che dữ liệu cá nhân, có cùng độ dài ký tự; chỉ bản này được gửi cho LLM bên thứ ba. |
| Placeholder | Chuỗi ký tự thay thế một đoạn dữ liệu cá nhân, cùng độ dài với đoạn bị thay. |
| Clause | Một điều khoản do bước tách điều khoản sinh ra, có clause_id, original_text và span. |
| Span | Cặp start_char (bao gồm) và end_char (không bao gồm) trên canonical text, tính theo Unicode code point sau NFC. Vì masked text cùng độ dài theo code point nên cùng span áp dụng cho cả hai. |
| Clause taxonomy | Tập 12 nhãn mô tả loại điều khoản. Tách biệt với risk taxonomy. |
| Risk taxonomy | Tập nhãn mô tả loại rủi ro theo vai trò. Taxonomy khai báo severity theo (nhãn, basis_type, vai trò); basis_type (LEGAL_VIOLATION, UNFAVORABLE hoặc AMBIGUOUS) là loại căn cứ của rủi ro trên một clause, do LLM chọn. Một clause có thể có nhiều risk label. |
| Kho luật | Nguồn đóng (closed corpus) duy nhất mà hệ thống được phép trích dẫn. |
| Candidate | Điều luật do retriever cung cấp cho một clause; LLM chỉ được chọn citation trong danh sách candidate. |
| Evidence status | SUPPORTED nếu có căn cứ từ candidate; INSUFFICIENT_EVIDENCE nếu thiếu căn cứ. |
| Data Graph | Đồ thị trên kho luật: nút là LegalProvision, cạnh là LegalEdge (cấu trúc, dẫn chiếu, hướng dẫn thi hành). Phục vụ Retrieval & Fact-finding: mở rộng và xếp hạng candidate (FR-12, FR-30). |
| Clause Graph | Đồ thị trên các clause của một phiên: nút là clause_id, cạnh là ClauseEdge. Tạo cục bộ, chỉ chứa ID và loại cạnh, xóa cùng phiên. Phục vụ Validation & Reasoning bằng cách chọn related clauses làm context cho Risk stage; không có quyền sửa quote/span (FR-31). |
| ContextResolutionTrace | Artifact chẩn đoán/evaluation chỉ chứa target clause_id, related clause_ids, loại quan hệ và graph flag; không chứa contract text. Dùng để chứng minh Clause Graph đã cung cấp context cho Risk stage (EV-09). |
| Retrieval nền | Truy xuất không dùng graph (bảng ánh xạ nhãn sang điều luật cộng tìm kiếm văn bản). Graph chỉ mở rộng trên kết quả của retrieval nền. |
