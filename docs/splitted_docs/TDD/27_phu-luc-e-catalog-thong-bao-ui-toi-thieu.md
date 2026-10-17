<!-- nguồn: TDD_AI_Labor_Contract_Risk_Analyzer_v0.2.md | mục: Phụ lục E. Catalog thông báo UI tối thiểu | 1518 ký tự | trước: 26_phu-luc-d-checklist-truoc-khi-khoa-demo.md | sau: 28_nguon-tai-lieu-dung-cho-tdd.md -->

# Phụ lục E. Catalog thông báo UI tối thiểu

| Code/state | Thông báo tiếng Việt đề xuất |
|---|---|
| SYSTEM_BUSY | Hệ thống đang xử lý một hợp đồng khác. Vui lòng thử lại sau. |
| QUOTA_EXCEEDED | Hệ thống đã đạt giới hạn phân tích hiện tại. Vui lòng thử lại sau. |
| RATE_LIMITED | Bạn gửi yêu cầu quá nhanh. Vui lòng chờ rồi thử lại. |
| UNSUPPORTED_FILE_TYPE | Chỉ hỗ trợ tệp PDF hoặc DOCX có sẵn văn bản. |
| FILE_TOO_LARGE | Tệp vượt giới hạn dung lượng cho phép. |
| PDF_PAGE_LIMIT_EXCEEDED | PDF vượt giới hạn số trang cho phép. |
| DOCX_TEXT_LIMIT_EXCEEDED | DOCX có nội dung vượt giới hạn ký tự cho phép. |
| NO_EXTRACTABLE_TEXT | Không trích xuất được văn bản. Hệ thống chưa hỗ trợ tệp scan/ảnh. |
| UNSUPPORTED_TEXT_ENCODING | Văn bản trích xuất không đọc được hoặc dùng mã/font chưa hỗ trợ. |
| NOT_LABOR_CONTRACT | Tài liệu không được nhận diện là hợp đồng lao động trong phạm vi hệ thống. |
| TOO_MANY_CLAUSES | Hợp đồng có quá nhiều điều khoản để xử lý trong bản demo. |
| AI_TIMEOUT / AI_PROVIDER_ERROR | Dịch vụ phân tích tạm thời gặp lỗi. Bạn có thể thử lại nếu phiên cho phép. |
| AI_OUTPUT_INVALID | Kết quả AI không đúng định dạng kỹ thuật. Bạn có thể thử lại nếu phiên cho phép. |
| REJECTED | Tệp đã bị từ chối; muốn thử tệp khác cần mở phiên mới. |
| INSUFFICIENT_EVIDENCE | Chưa đủ căn cứ pháp lý trong kho luật. |
| COMPLETED no-risk | Không phát hiện rủi ro trong phạm vi phân tích. Kết quả không đồng nghĩa hợp đồng an toàn. |
| EXPIRED | Phiên đã kết thúc và dữ liệu phiên đã được xóa. |
