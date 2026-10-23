<!-- nguồn: SRS_AI_Labor_Contract_Risk_Analyzer_1_4.md | mục: SRS: AI Labor Contract Risk Analyzer (phiên bản 1.4) > 10. Quy tắc nghiệp vụ bắt buộc | 2807 ký tự | trước: 11_9-giao-dien-thuc-thi-toi-thieu.md | sau: 13_11-truy-vet-brd-va-srs.md -->

## 10. Quy tắc nghiệp vụ bắt buộc

| ID | Quy tắc | So với 1.1 |
|---|---|---|
| R-01 | Vai trò phải được chọn trước upload và không đổi trong phiên. | Giữ |
| R-02 | Một phiên chỉ phân tích một hợp đồng. File bị REJECTED kết thúc phiên và không được xem là kết quả phân tích thành công. | Sửa |
| R-03 | Chỉ phân tích rủi ro trên clause hiện có; missing-clause risk ngoài phạm vi. | Giữ |
| R-04 | Che dữ liệu cá nhân chạy trên toàn canonical_text trước khi tách điều khoản; masked_text có cùng độ dài canonical_text. Tách điều khoản chạy trên masked_text; span áp dụng nguyên cho canonical_text (DEC-01). | Đổi |
| R-05 | Chỉ masked text được gửi tới LLM bên thứ ba. | Giữ |
| R-06 | Output của LLM join bằng clause_id; backend sở hữu quote, span và highlight. | Giữ |
| R-07 | Clause taxonomy và risk taxonomy tách biệt, được đóng băng và đánh version trước khi gán nhãn test. | Giữ |
| R-08 | Severity là HIGH, MEDIUM hoặc LOW; là null khi evidence_status = INSUFFICIENT_EVIDENCE. | Sửa |
| R-09 | Chỉ cite candidate từ closed legal corpus và version đang hiệu lực tại ngày phân tích. | Giữ |
| R-10 | Không đủ evidence thì không fabricate citation; giữ bản ghi với INSUFFICIENT_EVIDENCE (DEC-12). | Sửa |
| R-11 | Không đưa lời khuyên pháp lý hoặc gợi ý sửa, đàm phán. | Giữ |
| R-12 | FAILED không trả partial final report. REJECTED dành cho input không hợp lệ hoặc ngoài phạm vi và là trạng thái cuối. Chỉ FAILED được thử lại, tối đa 2 lần mỗi phiên. | Sửa |
| R-13 | Quote khi export là original_text từ canonical text; masked_text không dùng cho highlight hay export quote. | Giữ |
| R-14 | Kết quả không phát hiện rủi ro phải có disclaimer và không đồng nghĩa hợp đồng an toàn. | Giữ |
| R-15 | Tại một thời điểm chỉ một phiên ở trạng thái VALIDATING hoặc PROCESSING (FR-26). | Mới |
| R-16 | Điều khoản có lợi hơn mức pháp luật yêu cầu cho một vai trò không bị gắn rủi ro cho vai trò đó (BRD 3.2). | Mới |
| R-17 | Data Graph chỉ mở rộng candidate trong closed corpus và hiệu lực tại ngày phân tích; hệ thống phải chạy đúng khi tắt mở rộng (FR-30, DEC-21). | Mới |
| R-18 | Clause Graph chỉ chứa clause_id và loại cạnh; không có thẩm quyền đối với quote, span và highlight (FR-31). | Mới |
| R-19 | `basis_type` do LLM chọn một lần cho mỗi clause; backend phải kiểm (label, basis_type, vai trò) theo risk taxonomy và dựng `risk_basis`; severity do backend tra bảng, LLM không trả. | Mới 1.4 |
| R-20 | Span dùng Unicode code point sau NFC và các clause span không chồng lấn; nested structure không được tạo hai quote/highlight phủ cùng body text. | Mới 1.4 |
| R-21 | Manual retry phải giành lại processing slot; lỗi local quay lại VALIDATING, lỗi processing quay lại PROCESSING; SYSTEM_BUSY không tiêu hao retry count. | Mới 1.4 |
| R-22 | EV-08 graph on/off phải dùng cùng final candidate budget; primary M8 dùng predicted clause labels. | Mới 1.4 |
