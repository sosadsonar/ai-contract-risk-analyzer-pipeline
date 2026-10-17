<!-- nguồn: BRD_AI_Labor_Contract_Risk_Analyzer_0_5.md | mục: BRD: AI Labor Contract Risk Analyzer > 2. Phạm vi | 2096 ký tự | trước: 01_1-tong-quan.md | sau: 03_3-ben-lien-quan-va-dinh-nghia-rui-ro.md -->

## 2. Phạm vi

### 2.1 Trong phạm vi

* Web app cho máy tính, giao diện tiếng Việt, không cần đăng ký tài khoản.
* Đầu vào: HĐLĐ tiếng Việt, định dạng PDF hoặc DOCX có sẵn text, đã soạn đầy đủ điều khoản và chưa ký.
* Chọn vai trò (NLĐ hoặc NSDLĐ) cùng chỗ với nút Upload. Mỗi lần upload một hợp đồng.
* Phân loại từng điều khoản theo 12 nhãn đã được định nghĩa (clause [taxonomy](https://github.com/24021368-DucAnh/ai-contract-risk-analyzer/blob/main/docs/clause_taxonomy_v03.md?plain=1)).
* Đánh giá điều khoản có mức độ rủi ro như nào, rủi ro đó là gì (risk taxonomy).
* Báo cáo rủi ro gồm: điều khoản rủi ro, giải thích theo luật, điều luật liên quan, mức độ nghiêm trọng, highlight trên văn bản gốc. Cho phép xuất báo cáo
* Ẩn dữ liệu cá nhân.
* Data Graph (đồ thị kho luật, phục vụ Retrieval & Fact-finding, tức truy xuất căn cứ pháp lý) và Clause Graph (đồ thị điều khoản của hợp đồng trong phiên, phục vụ Validation & Reasoning: kiểm tra mâu thuẫn, suy diễn điều kiện), theo yêu cầu của giảng viên. Chi tiết thiết kế ở SDD và TDD (OI-14, OI-17).
* Disclaimer: kết quả chỉ mang tính tham khảo.

### 2.2 Ngoài phạm vi

* Chatbot hoặc hỏi đáp tiếp sau khi có kết quả. Sản phẩm không phải chatbot.
* Lời khuyên pháp lý, gợi ý sửa điều khoản, đề xuất thương lượng.
* Missing-clause risks: Rủi ro thiếu hoàn toàn 1 điều khoản bắt buộc
* So sánh các phiên bản của cùng một hợp đồng.
* PDF scan, ảnh chụp, OCR.
* Hợp đồng mẫu (template).
* Hợp đồng không phải tiếng Việt.
* Tài khoản, lịch sử lâu dài, thanh toán, gói đăng ký.
* Nhiều phiên xử lý song song.
* Ứng dụng di động, giao diện tiếng Anh.
* Tự huấn luyện hoặc tự host model.
* Quy mô và độ ổn định ở mức production.

### 2.3 Phạm vi nguồn luật

Kho luật gồm các nhóm văn bản sau, nạp theo thứ tự ưu tiên từ 1 đến 5:

1. Bộ luật Lao động 2019 và các nghị định hướng dẫn liên quan.
2. Nhóm luật về bảo hiểm.
3. Nhóm luật về thuế và dữ liệu cá nhân.
4. Luật nền về hợp đồng và doanh nghiệp, trong đó có Bộ luật Dân sự.
5. Nhóm về chế tài và giải quyết tranh chấp.

Hệ thống chỉ được trích dẫn văn bản có trong kho (yêu cầu BR-07 và BR-15).
