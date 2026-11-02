# BACKEND_ISSUES.md — Vấn đề liên quan backend (N5 duy trì)

> Cập nhật ngày: 2026-11-01. Nguồn: tài liệu bàn giao N5_API_HANDOFF_W3 của N4 (branch backend/n4-w3).
> KHÔNG tự sửa code backend ngoài `backend/app/result/`.

## Đã xử lý (không còn việc)

- **Retry:** `POST /sessions/{id}/retry` đã trả cùng cấu trúc với `GET /status` (B1).
- **Thời gian:** `created_at` và `updated_at` đều là UTC kết thúc bằng `Z` (B5).
- **Mã lỗi:** `api_error()` có giá trị mặc định cho code lạ; `FEATURE_NOT_ENABLED` luôn có sẵn trong `errors.py` (B6).
- **Fixture:** `tests/fixtures/mock_final_result_v1.json` đã được backend kiểm: offset theo code point, có ký tự 📄 ngoài BMP, nhãn hợp taxonomy (B2).
- **Phiên bản taxonomy:** thống nhất `risk_taxonomy_v01` (B3).

## Đang mở

### 1. Route export DOCX hiện tại sẽ được thay ở tuần 5 [Ghi chú]
**File:** `backend/app/api/routes/sessions.py` (route `/export`).
**Hiện trạng:** dùng `python-docx` trực tiếp trong route, không qua `ReportModel`.
**Kế hoạch:** tuần 5 (C-21b), N5 viết `backend/app/result/export_docx.py` dùng `build_report_model()`.
**Cần thống nhất với N4:** khi `export_docx` xong thì route `/export` gọi `build_report_model` -> `export_docx`. Không sửa route trước khi có `export_docx`.

### 2. CORS khi triển khai khác origin [Tùy chọn]
**File:** `backend/app/main.py` — chưa có `CORSMiddleware`.
**Ảnh hưởng:** dev không bị (Vite proxy `/api`). Chỉ cần nếu deploy frontend và backend ở hai origin khác nhau.

## Chờ nhóm duyệt (không tự sửa baseline BRD/SRS/SDD/TDD)

- TDD §5.5: ghi rõ body của Retry là cấu trúc status đầy đủ.
- TDD §5.3: ghi rõ quy ước `stage`/`progress` ở trạng thái cuối (hiện backend trả `stage="ASSEMBLY"` khi COMPLETED, `progress={0,0}` khi EXPIRED; frontend chấp nhận cả hai).
- SRS §6.2: `SESSION_NOT_ACCEPTING_UPLOAD` — ghi "ngoài phạm vi demo" nếu không có luồng upload vào phiên cũ.