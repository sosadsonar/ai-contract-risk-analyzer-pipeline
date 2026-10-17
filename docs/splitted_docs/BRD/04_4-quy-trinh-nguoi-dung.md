<!-- nguồn: BRD_AI_Labor_Contract_Risk_Analyzer_0_5.md | mục: BRD: AI Labor Contract Risk Analyzer > 4. Quy trình người dùng | 1478 ký tự | trước: 03_3-ben-lien-quan-va-dinh-nghia-rui-ro.md | sau: 05_5-yeu-cau-nghiep-vu.md -->

## 4. Quy trình người dùng

### 4.1 Luồng chính

1. Người dùng mở web app, không cần đăng nhập. Màn hình hiển thị disclaimer và thông báo về dữ liệu cá nhân.
2. Chọn vai trò (NLĐ hoặc NSDLĐ) ở cạnh nút Upload.
3. Upload một file hợp đồng.
4. Hệ thống kiểm tra định dạng, kích thước và việc file có text.
5. Hệ thống trích văn bản thô, ẩn dữ liệu cá nhân (PII Masking), thực hiện Clause Segmentation (tách điều khoản giữ nguyên tọa độ/offset văn bản gốc), phân loại loại điều khoản (Clause Classification qua Gemini Flash).
6. Hệ thống phân tích rủi ro theo vai trò, đối chiếu với kho luật.
7. Hệ thống hiển thị báo cáo: danh sách điều khoản rủi ro, highlight trên văn bản gốc.
8. Người dùng có thể chọn xuất kết quả ra file PDF/docx
9. Khi phiên kết thúc, dữ liệu bị xóa theo mục 7.

### 4.2 Luồng ngoại lệ

| Tình huống | Hành vi mong muốn |
|---|---|
| Định dạng không hỗ trợ | Từ chối, nêu rõ định dạng được hỗ trợ |
| File vượt giới hạn dung lượng hoặc số trang | Từ chối, nêu giới hạn |
| PDF không có text (scan, ảnh) | Báo chưa hỗ trợ file scan |
| Nội dung không giống HĐLĐ | Báo và không phân tích |
| Lỗi hoặc quá thời gian khi gọi LLM | Báo lỗi, cho thử lại, không hiển thị kết quả dở dang |
| Không phát hiện rủi ro | Hiển thị kết quả đó kèm disclaimer, không khẳng định hợp đồng an toàn |
| Hệ thống đang xử lý phiên khác | Từ chối phiên mới, báo thử lại sau. |
| Phiên hết hạn (60 phút không hoạt động) | Dữ liệu đã bị xóa, báo phiên hết hạn và mời mở phiên mới. |
