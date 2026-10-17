<!-- nguồn: BRD_AI_Labor_Contract_Risk_Analyzer_0_5.md | mục: BRD: AI Labor Contract Risk Analyzer > 1. Tổng quan | 2798 ký tự | trước: 00_brd-ai-labor-contract-risk-analyzer.md | sau: 02_2-pham-vi.md -->

## 1. Tổng quan

### 1.1 Bối cảnh và vấn đề

Phần lớn người ký hợp đồng lao động (HĐLĐ) không đủ kiến thức pháp lý để biết điều khoản nào bất lợi hoặc trái luật. Người lao động (NLĐ) thường chỉ nhận được bản hợp đồng để ký. Người sử dụng lao động (NSDLĐ), đặc biệt là doanh nghiệp nhỏ không có bộ phận pháp chế, có thể soạn điều khoản không phù hợp pháp luật và phải chịu rủi ro tranh chấp hoặc xử phạt. Cùng một điều khoản có thể là rủi ro với bên này nhưng không phải với bên kia, nên phân tích phải theo vai trò.

Hai phương án thay thế hiện nay đều có điểm yếu. Thuê luật sư thì tốn kém và chậm. Hỏi các LLM thông dụng (ví dụ ChatGPT) thì nhanh và rẻ nhưng dễ bịa nội dung hoặc trích dẫn sai điều luật.

### 1.2 Mục tiêu nghiệp vụ

Sản phẩm là một web app: người dùng chọn vai trò, tải HĐLĐ lên và nhận báo cáo rủi ro có căn cứ pháp luật.

* BO-1: có bản demo chạy full luồng từ upload đến báo cáo trong 8 tuần.
* BO-2: mọi rủi ro nêu ra đều gắn với điều khoản gốc và điều luật có thật trong kho luật của hệ thống và liên quan đến rủi ro đó. Rủi ro không có căn cứ trong kho luật được gắn nhãn "chưa đủ căn cứ" (BR-15), không bị gán điều luật.
* BO-3: cùng một hợp đồng, kết quả (loại rủi ro, mức độ nghiêm trọng, giải thích) thay đổi theo vai trò đã chọn. Nghiệm thu bằng các ca mẫu ở mục 3.3 và 8.6
* BO-4: dữ liệu cá nhân trong hợp đồng được ẩn trước khi gửi cho LLM bên thứ ba, đạt ngưỡng theo loại ở 7.3.
* BO-5: có Data Graph (đồ thị kho luật, phục vụ Retrieval & Fact-finding: tìm kiếm thông tin, truy vấn tri thức, tức truy xuất căn cứ pháp lý) và Clause Graph (đồ thị điều khoản của hợp đồng đang phân tích, phục vụ Validation & Reasoning: kiểm tra mâu thuẫn, suy diễn điều kiện) theo yêu cầu của giảng viên. Nghiệm thu bằng BR-17, BR-18 và M8 báo có và không dùng Graph (8.3).

### 1.3 Chỉ số thành công

| Mục tiêu | Chỉ số đo | Nơi định nghĩa |
|---|---|---|
| BO-1: luồng chính chạy trọn | Tiêu chí hoàn thành luồng; thời gian phân tích | 8.6; 6 |
| BO-2: gắn điều khoản gốc, điều luật có thật và liên quan | M3a, M3b, M4, M8 | 8.3 |
| BO-3: kết quả đổi theo vai trò | Ca mẫu theo vai trò | 3.3, §.6 |
| BO-4: ẩn dữ liệu cá nhân | Ngưỡng PII theo loại | 7.3 |
| Chất lượng phân tích | M1, M2, M5, M7 | 8.3 |
| Độ tin cậy của phép chấm | M6 | 8.3 |
| Tốt hơn LLM thông dụng | BL-1 | 8.3 |
| BO-5: Data Graph và Clause Graph | BR-17, BR-18; M8 có và không Graph | 5; 8.3 |

### 1.4 So sánh với phương án thay thế

| Phương án | Chi phí | Tốc độ | Điểm yếu |
|---|---|---|---|
| Luật sư | Cao | Chậm | Chi phí, phải hẹn và chờ |
| LLM thông dụng | Thấp | Nhanh | Dễ bịa nội dung, trích dẫn sai điều luật |
| Sản phẩm này | Miễn phí (demo) | Vài phút | Không thay thế tư vấn pháp lý; chất lượng phụ thuộc database luật; mức vượt trội so với LLM thông dụng cần được kiểm chứng (mục 8) |
