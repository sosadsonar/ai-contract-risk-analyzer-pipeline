<!-- nguồn: SRS_AI_Labor_Contract_Risk_Analyzer_1_4.md | mục: SRS: AI Labor Contract Risk Analyzer (phiên bản 1.4) > 6. Trạng thái xử lý và mã lỗi | 4064 ký tự | trước: 07_5-quy-tac-legal-retrieval-va-citation.md | sau: 09_7-yeu-cau-phi-chuc-nang-cho-demo.md -->

## 6. Trạng thái xử lý và mã lỗi

### 6.1 State machine

UPLOADED -> VALIDATING -> REJECTED                  (input/file/out-of-scope; cuối)
                 |
                 +-----> FAILED                   (lỗi nội bộ local)
                 |
                 +-----> PROCESSING -> COMPLETED
                              |
                              +-----> FAILED

FAILED --manual retry--> VALIDATING   nếu failed stage thuộc local validating stages
FAILED --manual retry--> PROCESSING   nếu failed stage thuộc processing stages
COMPLETED | FAILED | REJECTED -> EXPIRED

| State | Ý nghĩa |
|---|---|
| UPLOADED | File đã được nhận. |
| VALIDATING | Mọi bước cục bộ trước lệnh gọi LLM đầu tiên: kiểm tra file, trích text, kiểm tra phạm vi, che dữ liệu cá nhân, tách điều khoản và kiểm tra trần số clause. |
| REJECTED | Input không hợp lệ hoặc ngoài phạm vi; không phải lỗi pipeline. Trạng thái cuối, không thử lại. |
| PROCESSING | Đang chạy các bước có gọi LLM, retrieval và ghép kết quả. |
| COMPLETED | Có final result đầy đủ hoặc kết quả không phát hiện rủi ro. |
| FAILED | Input đã qua admission nhưng pipeline/local system/provider lỗi; không trả partial report. Manual retry tối đa 2 lần và phải acquire lại processing slot; target state phụ thuộc failed stage. |
| EXPIRED | Dữ liệu phiên đã bị xóa. Hệ thống giữ bản ghi chỉ gồm session_id và status trong thời gian cấu hình (mặc định 24 giờ), sau đó trả SESSION_NOT_FOUND. |

### 6.2 Mã lỗi tối thiểu

| Mã | Tình huống | State hoặc hành vi | Thử lại được |
|---|---|---|---|
| UNSUPPORTED_FILE_TYPE | Không phải PDF hoặc DOCX | REJECTED | Không |
| FILE_TOO_LARGE | Lớn hơn 10MB | REJECTED | Không |
| PDF_PAGE_LIMIT_EXCEEDED | PDF quá 30 trang | REJECTED | Không |
| DOCX_TEXT_LIMIT_EXCEEDED | DOCX có canonical text quá 100.000 ký tự | REJECTED | Không |
| NO_EXTRACTABLE_TEXT | Scan, image-only hoặc text rỗng | REJECTED | Không |
| UNSUPPORTED_TEXT_ENCODING | Text extraction không đọc được hoặc Unicode lỗi theo quality check (gồm PDF font cũ) | REJECTED | Không |
| NOT_LABOR_CONTRACT | Ngoài phạm vi HĐLĐ | REJECTED | Không |
| TOO_MANY_CLAUSES | Quá 150 clause | REJECTED | Không |
| ROLE_REQUIRED | Upload không kèm vai trò | Từ chối request, không tạo phiên | Có, gửi lại kèm vai trò |
| SESSION_NOT_ACCEPTING_UPLOAD | Phiên đã nhận file hoặc đã kết thúc | Từ chối request | Không, mở phiên mới |
| SYSTEM_BUSY | Đang có phiên xử lý khác | Từ chối request, không tạo phiên | Có, sau |
| QUOTA_EXCEEDED | Vượt trần call LLM trong ngày | Từ chối request, không tạo phiên | Có, sau |
| RATE_LIMITED | Vượt giới hạn tần suất theo IP | Từ chối request | Có, sau |
| AI_TIMEOUT | Một lệnh gọi LLM quá 30 giây sau auto-retry | FAILED | Có, thủ công |
| AI_PROVIDER_ERROR | Nhà cung cấp lỗi không phục hồi, gồm HTTP 429 sau auto-retry | FAILED | Có, thủ công |
| AI_OUTPUT_INVALID | Output LLM sai schema sau auto-retry | FAILED | Có, thủ công |
| INVALID_SESSION_STATE | Operation không hợp lệ với state hiện tại, ví dụ retry khi không FAILED | Từ chối operation, state không đổi | Tùy operation |
| RETRY_LIMIT_EXCEEDED | Thử lại thủ công lần thứ 3 | Từ chối request, state giữ FAILED | Không |
| SESSION_NOT_READY | Get Result/Export khi VALIDATING, PROCESSING hoặc FAILED | Từ chối operation, state không đổi | Có, khi state phù hợp |
| SESSION_REJECTED | Get Result/Export trên session REJECTED | Từ chối; nguyên nhân gốc nằm ở status.error_code | Không |
| SESSION_EXPIRED | Truy cập nội dung khi còn tombstone EXPIRED | Từ chối nội dung; status vẫn có thể trả EXPIRED | Không |
| FEATURE_NOT_ENABLED | Yêu cầu feature đã bị cắt, hiện dùng cho PDF export nếu cut item 4 áp dụng | Từ chối operation | Không |
| SESSION_NOT_FOUND | session_id không tồn tại hoặc đã hết thời gian giữ bản ghi EXPIRED | Từ chối request | Không |
| INTERNAL_ERROR | Lỗi backend hoặc pipeline khác | FAILED | Có, thủ công |
| LEGAL_CORPUS_CONFLICT | Metadata, version kho luật hoặc cạnh Data Graph mâu thuẫn | Lỗi khi build hoặc reload index (fail fast); không có state cho người dùng | Không, sửa dữ liệu |
