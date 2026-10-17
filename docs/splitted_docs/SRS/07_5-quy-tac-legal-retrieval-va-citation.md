<!-- nguồn: SRS_AI_Labor_Contract_Risk_Analyzer_1_4.md | mục: SRS: AI Labor Contract Risk Analyzer (phiên bản 1.4) > 5. Quy tắc legal retrieval và citation | 1922 ký tự | trước: 06_4-yeu-cau-du-lieu.md | sau: 08_6-trang-thai-xu-ly-va-ma-loi.md -->

## 5. Quy tắc legal retrieval và citation

* Kho luật là closed corpus duy nhất cho citation. LLM không được tự sinh tên luật, điều, khoản ngoài candidate list.
* Mỗi LegalProvision có version và effective_from, effective_to.
* Vì hợp đồng chưa ký, phiên bản pháp luật áp dụng mặc định theo ngày phân tích của hệ thống (system analysis date).
* Retriever chỉ đưa candidate có hiệu lực tại ngày phân tích. Nếu corpus có hai version chồng hiệu lực cho cùng một provision, đó là lỗi cấu hình dữ liệu: bị chặn khi build hoặc reload index (FR-24), không để người dùng gặp ở runtime; nếu vẫn lọt, provision đó bị loại khỏi candidate.
* Phương pháp retrieval chọn ở SDD và TDD, gồm retrieval nền và bước mở rộng qua Data Graph (FR-30, DEC-21). Yêu cầu tối thiểu: số candidate mỗi clause cấu hình được, và chất lượng đo bằng M8 (recall@5 trên lỗi chèn) như chỉ số chẩn đoán.
* Citation validation có ba lớp: (1) existence và version, tự động, M3a = 100%; (2) relevance, chấm tay hoặc judge đã hiệu chuẩn, M3b; (3) số citation LLM chọn ngoài candidate được log trước khi lọc để so sánh ở BL-1.
* evidence_status = SUPPORTED cần ít nhất một citation hợp lệ và liên quan. Rủi ro bất lợi hợp pháp (UNFAVORABLE) hoặc mơ hồ (AMBIGUOUS) mà không có điều luật trong kho thì có evidence_status = INSUFFICIENT_EVIDENCE; giao diện hiển thị loại rủi ro cùng dòng "chưa đủ căn cứ pháp lý trong kho luật" và không gán severity.
* Data Graph chỉ mở rộng và xếp hạng candidate, không tự tạo căn cứ. Mọi provision do mở rộng đưa vào phải qua cùng bộ lọc hiệu lực và thuộc kho như candidate thường; M3a vẫn 100%.
* Graph không thay retrieval nền: khi tắt mở rộng, hoặc graph lỗi bất thường lúc chạy, hệ thống dùng retrieval nền và ghi log. Trong EV-08, graph-on và graph-off phải có cùng final candidate budget; số candidate do graph thêm được log. Primary M8 dùng predicted clause labels từ pipeline; oracle-label diagnostic nếu có phải báo riêng.
