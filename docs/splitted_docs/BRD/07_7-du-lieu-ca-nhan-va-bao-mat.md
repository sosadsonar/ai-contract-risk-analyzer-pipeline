<!-- nguồn: BRD_AI_Labor_Contract_Risk_Analyzer_v0.6.md | mục: BRD: AI Labor Contract Risk Analyzer > 7. Dữ liệu cá nhân và bảo mật | 2717 ký tự | trước: 06_6-yeu-cau-phi-chuc-nang.md | sau: 08_8-do-luong-chat-luong-va-nghiem-thu.md -->

## 7. Dữ liệu cá nhân và bảo mật

### 7.1 Luồng xử lý dữ liệu

Luồng xử lý dữ liệu: file được upload, hệ thống trích văn bản, ẩn dữ liệu cá nhân ngay trong hệ thống của nhóm, chỉ văn bản đã ẩn được gửi cho LLM bên thứ ba, kết quả trả về được ánh xạ lại vào vị trí trong canonical text để highlight, và cuối cùng toàn bộ dữ liệu bị xóa.

### 7.2 Dữ liệu cần ẩn và cần giữ

**Cần ẩn:** họ tên (kể cả người đại diện), ngày sinh, số CCCD hoặc hộ chiếu, mã số thuế, ngày và nơi cấp giấy tờ, địa chỉ cư trú (ẩn toàn bộ, kể cả tỉnh) và địa chỉ trụ sở, số điện thoại, email, số tài khoản, tên pháp nhân (ẩn nguyên cụm), chữ ký.

**Cần giữ:** mức lương và phụ cấp, thời hạn hợp đồng, thời giờ làm việc, chức danh của NLĐ, chức vụ của người đại diện NSDLĐ, tên tỉnh khi đứng riêng, từ chỉ vai trò (vị trí), v.v. Hệ thống không giữ địa chỉ nên vùng lương tối thiểu không suy ra từ địa danh; kiểm tra mức lương dùng cận dưới của vùng IV (OI-19). Đây chính là dữ liệu cần để phát hiện rủi ro. Nếu ẩn hết mọi con số và địa danh thì phân tích sẽ mất độ chính xác.

### 7.3 Ngưỡng ẩn dữ liệu cá nhân

| Nhóm dữ liệu | Chỉ số | Ngưỡng |
|---|---|---|
| Số CCCD hoặc hộ chiếu, mã số thuế, số điện thoại, email, số tài khoản | Recall khi che | ≥ 99% |
| Họ tên (kể cả người đại diện), ngày sinh, ngày và nơi cấp giấy tờ, địa chỉ cư trú và trụ sở, tên pháp nhân, chữ ký | Recall khi che | ≥ 90% |
| Trường cần giữ (lương, phụ cấp, thời hạn, thời giờ, chức danh, chức vụ đại diện NSDLĐ, tỉnh khi đứng riêng, từ chỉ vai trò) | Tỷ lệ giữ nguyên | ≥ 95% |

Đo trên nội dung thực tế gửi cho LLM, bằng tập P1 có gold span (8.2); ngưỡng không phải 100% nên có rủi ro ở mục 10. Đây là mục tiêu cho demo, không phải cam kết với người dùng (Phụ lục A).

### 7.4 Lưu và xóa

**Lưu và xóa:** file gốc và kết quả chỉ tồn tại trong phiên. Đề xuất xóa khi người dùng đóng phiên hoặc sau 60 phút không hoạt động. Nội dung hợp đồng không được ghi vào cơ sở dữ liệu hay kho bền vững; chỉ tồn tại trong bộ nhớ hoặc kho tạm bị xóa theo phiên.

### 7.5 Nhà cung cấp LLM

**Nhà cung cấp LLM:** Hệ thống sử dụng mô hình Gemini Flash (Paid Tier) thông qua API thay vì triển khai tự lưu trữ (self-host). Demo và đánh giá dùng gói trả phí. Gói miễn phí và model chạy cục bộ chỉ dùng cho phát triển với dữ liệu đã de-identify. Model id phải được cấu hình tường minh. Judge (Claude, mục 8.5) chỉ nhận dữ liệu đã che hoặc đã de-identify.

### 7.6 Pháp lý và dữ liệu dev, test

Pháp lý: nhóm cần xác nhận văn bản hiện hành về bảo vệ dữ liệu cá nhân áp dụng cho demo. Việc ẩn dữ liệu tự động không đạt 100%, vì vậy thông báo cho người dùng không nên cam kết tuyệt đối. Hợp đồng dùng cho dev và test là hợp đồng thật, được de-identify thủ công trước khi đưa vào kho mã.
