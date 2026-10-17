<!-- nguồn: BRD_AI_Labor_Contract_Risk_Analyzer_0_5.md | mục: BRD: AI Labor Contract Risk Analyzer > 5. Yêu cầu nghiệp vụ | 3601 ký tự | trước: 04_4-quy-trinh-nguoi-dung.md | sau: 06_6-yeu-cau-phi-chuc-nang.md -->

## 5. Yêu cầu nghiệp vụ

Tất cả yêu cầu dưới đây là bắt buộc (Must). Dự án không có yêu cầu mức Should hay Could.

| ID | Yêu cầu |
|---|---|
| BR-01 | Người dùng chọn vai trò NLĐ hoặc NSDLĐ trước khi upload. Không thể đổi vai trò trong khi đang phân tích. |
| BR-02 | Hệ thống nhận file PDF và DOCX có text. Một phiên chỉ phân tích một hợp đồng. Có thể xuất kết quả ra file PDF/docx. |
| BR-03 | Hệ thống từ chối file scan, ảnh và định dạng khác; từ chối HĐ không phải HĐLĐ. kèm thông báo rõ ràng. File bị từ chối -> kết thúc phiên; muốn thử file khác phải mở phiên mới |
| BR-04 | Hệ thống ẩn dữ liệu cá nhân trước khi gửi nội dung cho LLM bên thứ ba, đồng thời giữ lại thông tin cần cho việc đánh giá rủi ro (mục 7). |
| BR-05a | Mỗi rủi ro trích nguyên văn điều khoản trong hợp đồng (từ văn bản trích xuất), không diễn đạt lại. |
| BR-05b | Hệ thống lưu vị trí (character offset) của từng điều khoản trên văn bản trích xuất để highlight (BR-09). Vị trí do hệ thống tính, không do LLM tạo. |
| BR-05c | Đầu ra của mỗi bước xử lý ở dạng cấu trúc chuẩn (Structured Output, JSON Schema) đặt trong thư mục schemas của pipeline (hiện là ai_pipeline/schemas). Schema có version và khai báo các trường version (SRS FR-29). |
| BR-06 | Mỗi rủi ro có giải thích vì sao đó là rủi ro, dựa trên luật và theo vai trò đã chọn. |
| BR-07 | Mỗi rủi ro nêu điều luật liên quan (tên văn bản, điều, khoản). Chỉ trích dẫn văn bản có trong kho luật. |
| BR-08 | Mỗi rủi ro có mức độ nghiêm trọng theo thang do đã định nghĩa (H/M/L). Mức độ có thể khác nhau giữa hai vai trò. Rủi ro chưa đủ căn cứ không được gán mức độ |
| BR-09 | Các rủi ro được highlight trên văn bản đã trích xuất từ file gốc của người dùng (canonical text), bấm vào để xem chi tiết. Giao diện ghi rõ đây là văn bản trích xuất, không phải file gốc |
| BR-10 | Mọi màn hình kết quả hiển thị disclaimer: thông tin chỉ mang tính chất tham khảo, không phải tư vấn pháp lý. Hệ thống không kiểm tra rủi ro do thiếu điều khoản. |
| BR-11 | Nội dung báo cáo chỉ phân tích và liệt kê rủi ro. Không đưa lời khuyên pháp lý, không gợi ý sửa điều khoản. |
| BR-12 | Giao diện có dòng thông báo ngắn về việc xử lý dữ liệu cá nhân (nội dung đề xuất ở Phụ lục A). |
| BR-13 | Dữ liệu hợp đồng và kết quả bị xóa khi phiên kết thúc (mục 7). |
| BR-14 | Kho luật do Người phụ trách dữ liệu duy trì. Mỗi văn bản ghi phiên bản và ngày hiệu lực. Cập nhật kho luật  đòi hỏi sửa mã nguồn |
| BR-15 | Khi kho luật không đủ căn cứ cho một nhận định, hệ thống không tự suy ra điều luật. Nhận định đó được gắn nhãn ‘chưa đủ căn cứ’, không gán mức . Phải nói rõ trong kết quả trả về. |
| BR-16 | Hệ thống giới hạn dung lượng file, số điều khoản mỗi hợp đồng và số lượt gọi LLM mỗi ngày để chi phí vận hành không vượt phần ngân sách vận hành (\$5, mục 6). Vượt trần thì từ chối phiên mới; phiên đang chạy vẫn hoàn tất. |
| BR-17 | Hệ thống có Data Graph: biểu diễn văn bản, điều, khoản, điểm của kho luật và quan hệ giữa chúng (cấu trúc, dẫn chiếu, hướng dẫn thi hành), dùng để mở rộng và xếp hạng ứng viên căn cứ khi truy xuất. Truy xuất vẫn chỉ trả điều luật có trong kho và đang hiệu lực (BR-07), và hệ thống vẫn chạy đúng khi tắt phần mở rộng này. |
| BR-18 | Hệ thống có Clause Graph: biểu diễn các điều khoản của hợp đồng đang phân tích và quan hệ giữa chúng. Tạo cục bộ, chỉ chứa mã định danh điều khoản và loại quan hệ, xóa cùng phiên (BR-13), không được làm đổi nội dung trích hay vị trí (BR-05a, BR-05b). Mục đích: kiểm tra mâu thuẫn và suy diễn điều kiện giữa các điều khoản (Validation & Reasoning); cách dùng chi tiết ở các bước sau do SDD và TDD xác định (OI-14). |
