<!-- nguồn: BRD_AI_Labor_Contract_Risk_Analyzer_0_5.md | mục: BRD: AI Labor Contract Risk Analyzer > Phụ lục B: Thuật ngữ | 1601 ký tự | trước: 11_phu-luc-a-noi-dung-hien-thi-de-xuat.md | sau: 13_11-open-issues.md -->

## Phụ lục B: Thuật ngữ

| Thuật ngữ | Ý nghĩa |
|---|---|
| NSDLĐ | Người sử dụng lao động |
| Kho luật | Tập văn bản pháp luật được nạp vào hệ thống, là nguồn duy nhất để trích dẫn |
| Phiên | Một lần làm việc trên web app với một vai trò và một hợp đồng. Kết thúc khi người dùng bấm kết thúc hoặc sau 60 phút không hoạt động. Đổi vai trò hoặc đổi file là mở phiên mới |
| Canonical text | Văn bản chuẩn duy nhất trích từ tệp gốc; dùng để tách điều khoản, lưu vị trí và highlight |
| Clause Segmentation | Tách hợp đồng thành các điều khoản, giữ vị trí trên canonical text |
| Clause taxonomy | Tập 12 nhãn mô tả loại điều khoản |
| Risk taxonomy | Tập nhãn mô tả loại rủi ro theo vai trò; tách biệt với clause taxonomy |
| Gold | Nhãn chuẩn dùng để chấm: người sửa tay, LLM gán rồi người xác minh, hoặc lỗi chèn |
| Lỗi chèn | Điều khoản vi phạm do nhóm tạo, chèn vào hợp đồng sạch để đo recall (8.4) |
| D1, D2, T1, T2 | Các tập dữ liệu dev và test (8.2) |
| Output | Một bản ghi rủi ro gồm điều khoản, nhãn, giải thích và citation (8.3) |
| LLM-as-a-judge | Dùng một LLM để chấm chất lượng đầu ra theo rubric; chỉ dùng sau khi hiệu chuẩn (M6) |
| Data Graph | Đồ thị trên kho luật: nút là điều luật (đơn vị trích dẫn được), cạnh là quan hệ cấu trúc, dẫn chiếu, hướng dẫn thi hành. Phục vụ Retrieval & Fact-finding: mở rộng và xếp hạng ứng viên khi truy xuất (BR-17) |
| Clause Graph | Đồ thị trên các điều khoản của một hợp đồng trong một phiên; chỉ chứa mã điều khoản và loại quan hệ; xóa cùng phiên. Phục vụ Validation & Reasoning: kiểm tra mâu thuẫn, suy diễn điều kiện (BR-18) |

INSTRUCTION:
