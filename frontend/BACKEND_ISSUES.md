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

### 1. Route export DOCX [Đã xử lý 13/11]
`/export` gọi `build_report_model()` → `backend/app/result/export_docx.py` (C-21 b). Báo cáo có tóm tắt, số Điều,
"Liên quan", bản ghi cần xem xét, citation kèm nguyên văn Khoản, disclaimer + data notice.

### 2. CORS khi triển khai khác origin [Tùy chọn]
**File:** `backend/app/main.py` — chưa có `CORSMiddleware`.
**Ảnh hưởng:** dev không bị (Vite proxy `/api`). Chỉ cần nếu deploy frontend và backend ở hai origin khác nhau.

### 3. stage lạ từ backend khi COMPLETED [Đã xử lý phía frontend]
**Hiện tượng:** Backend có thể trả `stage="ASSEMBLY"` khi COMPLETED, `progress={0,0}` khi EXPIRED.
**Xử lý frontend:** `Progress.tsx` dùng `getStageName()` với fallback tên stage lạ → không làm trống UI.
**Cần backend ghi rõ:** TDD §5.3 chưa khóa quy ước stage/progress ở trạng thái cuối. Đề xuất N4 ghi errata.

### 4. T1 (ghép frontend–backend thật) [Một phần — 13/11]
- `smoke_api.mjs` chạy PASS với backend dev (chế độ fixture mẫu).
- Backend có chế độ pipeline thật không cần mạng: `DEV_LLM_PROVIDER=fake` (provider tất định). Đã thử HTTP
  upload DOCX → COMPLETED → result → export → End. **Còn lại:** chạy giao diện trong trình duyệt với
  `VITE_USE_MOCK=false` (kiểm highlight non-BMP INV-12, thẻ "cần xem xét", dòng "Liên quan").
- Lưu ý: ở chế độ pipeline, `norisk.pdf`/`insufficient.pdf` của smoke là PDF tối giản nên có thể bị
  REJECTED (`NO_EXTRACTABLE_TEXT`) — smoke đó chỉ dành cho chế độ fixture.

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
