# BACKEND_ISSUES.md — Vấn đề liên quan backend (N5 duy trì)

> Cập nhật ngày: 2026-11-08. Nguồn: tài liệu bàn giao N5_API_HANDOFF_W3 của N4 (branch backend/n4-w3) + rà soát tuần 4.
> KHÔNG tự sửa code backend ngoài `backend/app/result/`.

## Đã xử lý (không còn việc)

- **Retry:** `POST /sessions/{id}/retry` đã trả cùng cấu trúc với `GET /status` (B1).
- **Thời gian:** `created_at` và `updated_at` đều là UTC kết thúc bằng `Z` (B5).
- **Mã lỗi:** `api_error()` có giá trị mặc định cho code lạ; `FEATURE_NOT_ENABLED` luôn có sẵn trong `errors.py` (B6).
- **Fixture:** `backend/app/session/fixtures/mock_final_result_v1.json` (chuyển từ `tests/fixtures/` ở X-20) đã được backend kiểm: offset theo code point, có ký tự 📄 ngoài BMP, nhãn hợp taxonomy (B2).
- **Phiên bản taxonomy:** thống nhất `risk_taxonomy_v01` (B3). Comment sai "v02" trong `frontend/src/lib/labels.ts` đã sửa tuần 4.

## Đang mở

### 1. Route export DOCX hiện tại sẽ được thay ở tuần 5 [Ghi chú]
**File:** `backend/app/api/routes/sessions.py` (route `/export`).
**Hiện trạng:** dùng `python-docx` trực tiếp trong route, không qua `ReportModel`.
**Kế hoạch:** tuần 5 (C-21b), N5 viết `backend/app/result/export_docx.py` dùng `build_report_model()`.
**Cần thống nhất với N4:** khi `export_docx` xong thì route `/export` gọi `build_report_model` -> `export_docx`. Không sửa route trước khi có `export_docx`.

### 2. CORS khi triển khai khác origin [Tùy chọn]
**File:** `backend/app/main.py` — chưa có `CORSMiddleware`.
**Ảnh hưởng:** dev không bị (Vite proxy `/api`). Chỉ cần nếu deploy frontend và backend ở hai origin khác nhau.

### 3. stage lạ từ backend khi COMPLETED [Đã xử lý phía frontend]
**Hiện tượng:** Backend có thể trả `stage="ASSEMBLY"` khi COMPLETED, `progress={0,0}` khi EXPIRED.
**Xử lý frontend:** `Progress.tsx` dùng `getStageName()` với fallback tên stage lạ → không làm trống UI.
**Cần backend ghi rõ:** TDD §5.3 chưa khóa quy ước stage/progress ở trạng thái cuối. Đề xuất N4 ghi errata.

### 4. T1 (ghép frontend–backend thật) — chưa thực hiện trong sandbox [Mở]
**Lý do chưa chạy trong sandbox:**
- Môi trường thực thi sandbox hiện tại có MSYS2 Python 3.12 nhưng không có sẵn module `pip` (bị lỗi PEP 668 `externally-managed-environment`).
- Sandbox không có kết nối internet ra ngoài nên không thể chạy `python -m pip install -e '.[dev]'` để cài các dependency của backend (`fastapi`, `uvicorn`, `pymupdf`...).
- Do đó backend FastAPI chưa thể khởi động lắng nghe tại `http://127.0.0.1:8000` trong phiên này.

**Công cụ đã chuẩn bị để kiểm thử độc lập (không qua UI):**
- Đã viết script `frontend/scripts/smoke_api.mjs` (Node fetch thuần túy, không thêm package ngoài) để chạy smoke test API trực tiếp với backend dev theo đúng yêu cầu:
  1. POST /api/v1/sessions với role + file PDF (`norisk.pdf`, `insufficient.pdf`, `emoji.pdf`).
  2. Polling status cho đến trạng thái cuối (`COMPLETED`).
  3. GET /api/v1/sessions/{id}/result: kiểm tra đủ các khóa theo `src/api/types.ts` (`FinalResult`), offset là partition không chồng lấn, `canonical_text` khớp với `clauses`, `insufficient.pdf` thì `severity = null` và `citation_ids = []`.
  4. DELETE /api/v1/sessions/{id}: kiểm tra phiên chuyển thành `EXPIRED` (tombstone) hoặc `404 SESSION_NOT_FOUND`.
- Lệnh chạy: `cd frontend && npm run smoke:api` (hoặc `node frontend/scripts/smoke_api.mjs`).
- Khi chạy trên máy dev có backend: nếu phát hiện sai lệch hợp đồng nào giữa backend và `src/api/types.ts`, bổ sung vào mục này thay vì tự ý sửa backend.

## Chờ nhóm duyệt (không tự sửa baseline BRD/SRS/SDD/TDD)

- TDD §5.5: ghi rõ body của Retry là cấu trúc status đầy đủ.
- TDD §5.3: ghi rõ quy ước `stage`/`progress` ở trạng thái cuối (hiện backend trả `stage="ASSEMBLY"` khi COMPLETED, `progress={0,0}` khi EXPIRED; frontend chấp nhận cả hai).
- SRS §6.2: `SESSION_NOT_ACCEPTING_UPLOAD` — ghi "ngoài phạm vi demo" nếu không có luồng upload vào phiên cũ.

### Mâu thuẫn Phụ lục E vs TDD §5.9 về cụm từ "an toàn" [Chờ nhóm duyệt]
**Phát hiện:** `messages.ts` mục `NO_RISK` hiện có câu "Kết quả không đồng nghĩa hợp đồng an toàn" — đây là phủ định hợp lệ theo Phụ lục E (TDD Phụ lục E: "Kết quả không đồng nghĩa hợp đồng an toàn").
Tuy nhiên TDD §5.9 yêu cầu "không dùng từ 'an toàn'" một cách tuyệt đối.
**Giải thích N5:** Phụ lục E chính nó dùng cụm "không ... an toàn" dưới dạng phủ định, còn §5.9 cấm khẳng định "hợp đồng an toàn". Hai điều này không nhất quán.
**Quyết định tạm:** Giữ nguyên theo Phụ lục E (phủ định). Chờ nhóm duyệt để xác nhận hoặc đổi câu.
**File liên quan:** `frontend/src/lib/messages.ts` dòng `NO_RISK`.
