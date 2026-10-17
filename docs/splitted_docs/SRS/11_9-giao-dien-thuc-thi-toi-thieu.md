<!-- nguồn: SRS_AI_Labor_Contract_Risk_Analyzer_1_4.md | mục: SRS: AI Labor Contract Risk Analyzer (phiên bản 1.4) > 9. Giao diện thực thi tối thiểu | 1471 ký tự | trước: 10_8-chat-luong-ai-va-danh-gia.md | sau: 12_10-quy-tac-nghiep-vu-bat-buoc.md -->

## 9. Giao diện thực thi tối thiểu

SRS chỉ chốt các operation hệ thống phải cung cấp; tên endpoint và HTTP schema cuối cùng được khóa ở TDD/API Contract nhưng không được đổi ngữ nghĩa dưới đây. Mọi operation dùng session_id (DEC-03).

| Operation | Input chính | Output chính | Điều kiện và lỗi chính |
|---|---|---|---|
| Create/Upload | role, PDF hoặc DOCX | Nếu admission pass: session_id, status sớm; validate chạy tiếp bất đồng bộ | Admission errors ROLE_REQUIRED/SYSTEM_BUSY/QUOTA_EXCEEDED/RATE_LIMITED không tạo session. Các mã file/phạm vi/TOO_MANY_CLAUSES xuất hiện sau đó qua Get Status với state REJECTED. |
| Get Status | session_id | status, stage, manual_retry_count, error_code nếu có | SESSION_NOT_FOUND; không tính là hoạt động (FR-23) |
| Get Result | session_id | canonical_text, clauses, risks (gồm risk_basis), citations, disclaimer, data notice, offset unit | Chỉ COMPLETED; trạng thái khác dùng SESSION_NOT_READY / SESSION_REJECTED / SESSION_EXPIRED. |
| Retry | session_id | Nếu acquire slot thành công: tăng manual_retry_count và resume đúng state/stage | Chỉ FAILED; SYSTEM_BUSY không tăng counter; INVALID_SESSION_STATE nếu state khác; RETRY_LIMIT_EXCEEDED chỉ lần thứ 3. |
| Export Report | session_id, format (pdf hoặc docx) | File download | Chỉ khi COMPLETED |
| End Session | session_id | Xác nhận + status EXPIRED; hủy provider task đang chạy và cleanup | Xóa dữ liệu theo FR-23; operation idempotent khi tombstone EXPIRED còn tồn tại. |
