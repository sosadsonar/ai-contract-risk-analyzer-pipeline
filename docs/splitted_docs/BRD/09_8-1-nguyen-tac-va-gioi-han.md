<!-- nguồn: BRD_AI_Labor_Contract_Risk_Analyzer_v0.6.md | mục: BRD: AI Labor Contract Risk Analyzer > 8. Đo lường chất lượng và nghiệm thu > 8.1 Nguyên tắc và giới hạn | 770 ký tự | trước: 08_8-do-luong-chat-luong-va-nghiem-thu.md | sau: 10_8-2-du-lieu-danh-gia.md -->

### 8.1 Nguyên tắc và giới hạn

Nhóm không có luật sư và nhãn gold hiện có do LLM tạo. Vì vậy:

* Tầng nào kiểm tra tự động được bằng quy tắc xác định thì kiểm tự động, không dùng LLM.

* Mọi con số báo cáo phải kèm nguồn nhãn gold (người sửa, LLM gán rồi người xác minh, lỗi chèn) và kích thước tập test.

* LLM-as-a-judge chỉ dùng khi có bằng chứng trong tay (văn bản hợp đồng đã che, điều luật trong kho) và phải được hiệu chuẩn bằng người trước khi tin kết quả (M6). Judge không được dùng để quyết định false negative và không tham gia tính M5.

* Gold của taxonomy là sự đồng thuận của nhóm không có chuyên môn pháp lý, không phải chân lý pháp lý. Báo cáo phải nói rõ điều này.

Ngoài phạm vi: không đo false positive riêng. Precision nằm trong F1 của M1, M2 và M7.
