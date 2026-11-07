<!-- nguồn: T1_EQUIVALENT_GATE_EVALUATION_GUIDE.md | mục: Hướng dẫn cổng T1 tương đương và đọc kết quả đánh giá > 1. Quyết định cần nhớ | 1500 ký tự | trước: 00_huong-dan-cong-t1-tuong-duong-va-doc-ket-qua-danh.md | sau: 02_2-ba-lat-cat-bat-buoc-trong-bao-cao-t1.md -->

## 1. Quyết định cần nhớ

`D1 = HDLD001–004`, gồm 4 hợp đồng và 183 điều khoản đã REVIEWED. HDLD005 thuộc T1 trong mọi bước: không đưa vào few-shot, train hay tuning Dev. D2 gồm 4 tài liệu Dev HDLD001–004, 236 span phân đoạn và 30 lỗi chèn riêng (8 + 8 + 7 + 7). T2 mới gồm 9 tài liệu HDLD005–013, 872 span và 30 lỗi chèn. Không sử dụng Gold T1/T2 làm đầu vào dự đoán hoặc để điều chỉnh mô hình.

T1 được tiếp nhận theo `T1_EQUIVALENT_GATE_V1`, gồm 10 **tài liệu**, không phải 10 hợp đồng đã ký độc lập. Đây là quyết định nghiệm thu nội bộ của nhóm để có một tập đánh giá khả dụng trong điều kiện dữ liệu hợp đồng đã ký chứa PII cần hạn chế truy cập. Kết quả phải công bố cấu trúc mẫu và giới hạn của nó; không suy ra quyền công bố dữ liệu từ việc cổng đã đạt.

| Nhóm | ID | Số lượng | Cách xác minh và cách dùng |
|---|---|---|---|
| `REAL_EXECUTED_RESTRICTED` | HDLD010–013 | 4 | File lưu cục bộ có SHA-256 và Gold privacy khoanh vùng PII. Không đẩy văn bản gốc hoặc Gold chứa nội dung nhạy cảm lên Git công khai. Hash chứng minh danh tính byte của bản lưu, không chứng minh giấy phép, chữ ký hay quyền xử lý dữ liệu. |
| `PUBLIC_TEMPLATE_VERIFIED` | HDLD005–009 | 5 | Mẫu công khai; HDLD005 và HDLD006 cùng họ mẫu, được ghi là cặp đối chứng độ mịn phân đoạn. HDLD007 là phép thử dẫn chiếu ngoài corpus hiện có. |
| `SYNTHETIC_CALIBRATION_CONTROL` | HDLD014 | 1 | Đối chứng tổng hợp 10 điều khoản, 7 trường cần giữ, 0 PII thật. Chỉ dùng để hiệu chuẩn kỹ thuật; không trình bày như hợp đồng thật. |
