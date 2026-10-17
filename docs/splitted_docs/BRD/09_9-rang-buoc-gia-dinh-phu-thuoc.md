<!-- nguồn: BRD_AI_Labor_Contract_Risk_Analyzer_0_5.md | mục: BRD: AI Labor Contract Risk Analyzer > 9. Ràng buộc, giả định, phụ thuộc | 3609 ký tự | trước: 08_8-do-luong-chat-luong-va-nghiem-thu.md | sau: 10_10-rui-ro-du-an.md -->

## 9. Ràng buộc, giả định, phụ thuộc

### 9.1 Ràng buộc

* 10 tuần, 5 người: 8 tuần xây dựng đến demo (tuần đầu bắt đầu 12/10/2026, hạn demo 06/12/2026) và 2 tuần đánh giá T1, T2 và báo cáo (9.4). Đã xác nhận 12/10/2026 (OI-15).
* Không huấn luyện hoặc tự host model. Một số bước của pipeline gọi API LLM bên thứ ba.
* Ngân sách hạn chế (\$20)
* Không có luật sư hoặc chuyên gia pháp lý rà soát.
* Web máy tính, chỉ tiếng Việt.

### 9.2 Giả định do tài liệu đặt ra

| ID | Giả định |
|---|---|
| A1 | Loại hợp đồng chấp nhận: HĐLĐ tiếng Việt, gồm cả hợp đồng thử việc, phụ lục nằm trong cùng file. |
| A2 | Giới hạn file 10MB và 30 trang; DOCX 10MB 100k kí tự. |
| A3 | Kết quả của  hợp đồng đã phân tích có thể được xuất ra file PDF/docx. Sẽ mất khi phiên kết thúc. |
| A4 | Ngưỡng thời gian: < 2 phút cho hợp đồng 15 trang. 90% phiên được test đạt được hiệu năng này |
| A5 | Thang mức độ gồm 3 bậc (H/M/L) |
| A6 | Văn bản không giống HĐLĐ bị từ chối. |
| A7 | Một phiên gắn với một vai trò và một hợp đồng; đổi vai trò hoặc đổi file là mở phiên mới. |
| A8 | Hệ thống phục vụ một phiên đang xử lý tại một thời điểm. |

### 9.3 Phụ thuộc

* API LLM của nhà cung cấp bên thứ ba.
* Kho luật do người phụ trách dữ liệu xây dựng.
* Dịch vụ hosting cho web và backend.

### 9.4 Mốc thời gian (đề xuất)

| Mốc | Ngày | Nội dung |
|---|---|---|
| MS-1 | 25/10/2026 (hết tuần 2) | Đóng băng clause taxonomy, risk taxonomy, severity rubric, annotation guideline (SRS DEC-10). Risk taxonomy có người phụ trách và bản đầu (OI-01). Chốt danh mục kho luật tầng 1 (OI-02). |
| MS-2 | 08/11/2026 (hết tuần 4) | Chốt các cấu hình còn mở (SRS OI-03 đến OI-05, OI-09 đến OI-12). Bản đầu kho luật tầng 1 và Data Graph cấu trúc. Pipeline đến Clause Classification chạy trên D1. Che dữ liệu cá nhân có số đo đầu trên D1. |
| MS-3 | 06/12/2026 (hết tuần 8) | Demo full luồng cho cả hai vai trò. Khóa phiên bản hệ thống và ghi commit hash (SRS EV-07). |
| MS-4 | 13/12/2026 (hết tuần 9) | Chạy xong T1, T2, M1 đến M8, hiệu chuẩn judge (M6). |
| MS-5 | 20/12/2026 (hết tuần 10) | Báo cáo đánh giá và bảo vệ. |

MS-1 và MS-3 lấy từ SRS (DEC-10, DEC-14, EV-07); MS-2, MS-4, MS-5 là đề xuất chờ OI-05. Gán nhãn gold cho T1 và T2 chạy song song từ sau MS-1 đến trước MS-4 và không dùng gold để chỉnh hệ thống (8.2, quy tắc 7).

### 9.5 Thứ tự cắt tính năng

Khi trễ tiến độ, nhóm cắt từ trên xuống dưới và không cắt hạng mục khác khi chưa cắt hết hạng mục phía trên. Hạng mục 4 cần chủ sở hữu BRD duyệt vì BR-02 yêu cầu cả hai định dạng. Hạng mục 5 cần chủ sở hữu BRD và giảng viên duyệt vì BR-17 và BR-18 do giảng viên yêu cầu.

1. BL-1, so sánh với LLM thông dụng (§8.3).

2. Stage resume: retry chạy lại từ đầu, vẫn giữ hạn 2 lần thử lại thủ công mỗi phiên.

3. LLM hỗ trợ tách điều khoản: chỉ dùng luật và fallback theo paragraph.

4. Export PDF: chỉ giữ DOCX.

5. Graph: chỉ giữ cạnh cấu trúc; bỏ cạnh dẫn chiếu và hướng dẫn giữa các điều luật (REFERS_TO, GUIDES) và cạnh dẫn chiếu giữa các điều khoản (SRS FR-30, FR-31). Data Graph và Clause Graph vẫn phải có.

### 9.6 Phân công (đề xuất)

Theo vai trò ghi trong tài liệu của repo; chốt ở OI-04.

| Mảng | Phụ trách đề xuất |
|---|---|
| Tách và phân loại điều khoản (Clause AI) | Người 1 |
| Dữ liệu: kho luật, gold, nguồn cạnh Data Graph | Người 2 |
| Risk, severity, giải thích, citation (Risk AI) | Người 3 |
| Hệ thống: extraction, phiên, API, export | Người 4 |
| Giao diện, highlight, báo cáo | Người 5 |
| Chưa có chủ: risk taxonomy (OI-01), che dữ liệu cá nhân (SRS FR-10), dựng Data Graph và Clause Graph, harness đánh giá, pháp lý dữ liệu cá nhân (OI-03) | Cả nhóm |
