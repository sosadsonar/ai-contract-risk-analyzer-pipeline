<!-- nguồn: TDD_AI_Labor_Contract_Risk_Analyzer_v0.2.md | mục: 5. HTTP API Contract | 7110 ký tự | trước: 05_4-configuration-secret-va-startup.md | sau: 07_6-domain-model-va-json-schema.md -->

# 5. HTTP API Contract

## 5.1 Quy ước chung

* Base path: `/api/v1`. JSON UTF-8; upload dùng `multipart/form-data`.
* `session_id` là UUID v4 opaque.
* Error body: `{error:{code,message,retryable,details?}}`, message tiếng Việt.
* SRS 6.2 là **tập mã lỗi tối thiểu**. TDD định nghĩa thêm một số API-state code ở §5.8; chúng không tạo state mới và nên được backport vào SRS để truy vết.
* Polling Get Status không cập nhật `last_activity_at`. Get Result, Retry, Export, End Session là user activity.
* Không trả canonical/masked text trong error/log. Get Result chỉ trả canonical text khi COMPLETED.
* Không authentication trong demo; deployment dùng HTTPS.

## 5.2 POST /api/v1/sessions - Create/Upload

Upload dùng lifecycle **bất đồng bộ** để REJECTED luôn gắn với một session. Request entry thực hiện pre-admission gate theo thứ tự: validate role -> rate limit -> quota reservation -> `try_acquire()` processing lease. Nếu gate thất bại thì **không tạo session**. Khi gate thành công, backend tạo session, bắt đầu nhận file với hard byte cap, schedule pipeline và trả `201 Created` nhanh; mọi lỗi input/file phát hiện sau đó chuyển session sang REJECTED và client đọc `error_code` qua Get Status.

```http
POST /api/v1/sessions
Content-Type: multipart/form-data

role=EMPLOYEE
file=<contract.pdf>

201 Created
{
  "session_id": "f2c7...",
  "status": "UPLOADED",
  "created_at": "2026-10-12T14:20:00Z"
}
```

Các lỗi **không tạo session**:

| Tình huống | HTTP | error.code |
|---|---|---|
| Thiếu role | 400 | ROLE_REQUIRED |
| Processing lease đang bận | 409 | SYSTEM_BUSY |
| Không đủ quota reservation cho session mới | 429 | QUOTA_EXCEEDED |
| Vượt rate theo IP | 429 | RATE_LIMITED |

Các mã `UNSUPPORTED_FILE_TYPE`, `FILE_TOO_LARGE`, `PDF_PAGE_LIMIT_EXCEEDED`, `DOCX_TEXT_LIMIT_EXCEEDED`, `NO_EXTRACTABLE_TEXT`, `UNSUPPORTED_TEXT_ENCODING`, `NOT_LABOR_CONTRACT`, `TOO_MANY_CLAUSES` là **REJECTED của session**. Chúng không được trả như lỗi đồng bộ của POST sau khi session đã tạo.

Nếu upload stream bị ngắt trước khi file được nhận đủ, đây là lỗi pipeline/input của session và được map theo typed error phù hợp; processing lease vẫn release trong `finally`.

## 5.3 GET /api/v1/sessions/{session_id}/status

```json
{
  "session_id": "...",
  "status": "PROCESSING",
  "stage": "RISK_ANALYSIS",
  "manual_retry_count": 0,
  "progress": {"completed_units": 32, "total_units": 47},
  "error_code": null,
  "updated_at": "2026-10-12T14:20:18Z"
}
```

Với REJECTED/FAILED, `error_code` bắt buộc có. Với EXPIRED còn tombstone, trả `200 status=EXPIRED` nhưng không có contract content. Sau thời gian tombstone: `404 SESSION_NOT_FOUND`.

## 5.4 GET /api/v1/sessions/{session_id}/result

Chỉ COMPLETED trả 200. Các state khác dùng API-state code ở §5.8.

```json
{
  "schema_version": "final_result_v1",
  "offset_unit": "unicode_code_point",
  "session_id": "...",
  "role": "EMPLOYEE",
  "status": "COMPLETED",
  "analysis_date": "2026-10-12",
  "canonical_text": "...",
  "clauses": [
    {"clause_id":"cl_0001","original_text":"...","start_char":0,"end_char":128,
     "clause_labels":["COMPENSATION_BENEFITS"]}
  ],
  "risks": [
    {"clause_id":"cl_0001",
     "risk_labels":["PROBATION"],
     "risk_basis":[{"label":"PROBATION","basis_type":"LEGAL_VIOLATION"}],
     "severity":"HIGH","explanation":"...","evidence_status":"SUPPORTED",
     "citation_ids":["BLLD2019:art26"]}
  ],
  "citations": [
    {"citation_id":"BLLD2019:art26","document_name":"Bộ luật Lao động 2019",
     "article":"26","content":"..."}
  ],
  "disclaimer": "...",
  "data_notice": "...",
  "version_pins": {...}
}
```

`risk_basis` do backend dựng từ `basis_type` của LLM và `risk_labels` sau khi validate (label, basis_type, vai trò) theo risk taxonomy; `severity` do backend tra bảng.

## 5.5 POST /api/v1/sessions/{session_id}/retry

Chỉ status=FAILED và `manual_retry_count < 2`. Retry phải `try_acquire()` processing lease **trước** khi tăng counter. Nếu lease bận: `409 SYSTEM_BUSY`, counter không tăng. Nếu state không phải FAILED: `409 INVALID_SESSION_STATE`. Chỉ retry thứ 3 mới dùng `RETRY_LIMIT_EXCEEDED`.

Sau khi acquire lease, Orchestrator xác định `failed_stage`: lỗi ở local stage trước LLM #1 -> state quay lại VALIDATING; lỗi ở PROCESSING -> state PROCESSING. Resume từ stage lỗi nếu fingerprint hợp lệ; nếu cut stage-resume thì chạy lại từ đầu.

## 5.6 GET /api/v1/sessions/{session_id}/export?format=docx|pdf

Chỉ COMPLETED. Server build report in-memory/temp, stream file và xóa trong `finally`. Nếu PDF đã bị cắt, `format=pdf` trả `501 FEATURE_NOT_ENABLED`; DOCX vẫn bắt buộc.

## 5.7 DELETE /api/v1/sessions/{session_id}

End Session trả xác nhận + EXPIRED theo SRS:

```json
200 OK
{
  "session_id": "...",
  "status": "EXPIRED",
  "message": "Phiên đã kết thúc và dữ liệu phiên đã được xóa."
}
```

Operation idempotent: nếu session còn tồn tại, cancel tasks, cleanup, release lease nếu session sở hữu lease và ghi tombstone. Nếu tombstone đã tồn tại, trả cùng response EXPIRED. Chỉ `SESSION_NOT_FOUND` khi không có session/tombstone.

## 5.8 ErrorResponse và API-state code

```json
{
  "error": {
    "code": "INVALID_SESSION_STATE",
    "message": "Trạng thái phiên không cho phép thao tác này.",
    "retryable": false,
    "details": {"status":"COMPLETED"}
  }
}
```

| API-state code | Dùng khi | Ghi chú |
|---|---|---|
| INVALID_SESSION_STATE | Retry/operation không hợp lệ theo state | Không dùng thay RETRY_LIMIT_EXCEEDED. |
| SESSION_NOT_READY | Get Result/Export khi VALIDATING/PROCESSING/FAILED | State không đổi. |
| SESSION_REJECTED | Get Result/Export khi REJECTED | Chi tiết nguyên nhân lấy từ status.error_code. |
| SESSION_EXPIRED | Get Result/Export khi còn tombstone EXPIRED | HTTP 410. |
| FEATURE_NOT_ENABLED | PDF export bị cắt | Chỉ feature cut. |

Các code trên là chi tiết API của TDD vì SRS 6.2 ghi “mã lỗi tối thiểu”. Đề xuất cập nhật ngược SRS để traceability đầy đủ.

## 5.9 Frontend integration contract

* Sau 201, frontend bắt đầu polling status sau 500 ms; trong VALIDATING/PROCESSING poll mỗi 1,5 giây. Sau 60 giây có thể giảm xuống 2,5 giây. Dừng polling ở COMPLETED/FAILED/REJECTED/EXPIRED. Mục tiêu UI hiển thị VALIDATING/PROCESSING trong <=2 giây theo NFR-PERF-02.
* REJECTED: hiển thị thông báo theo `error_code`; không hiện nút Retry, chỉ cho mở phiên mới.
* FAILED: hiển thị lỗi + nút Retry khi `manual_retry_count < 2`; retry có thể trả SYSTEM_BUSY.
* COMPLETED + không risk: hiển thị “Không phát hiện rủi ro trong phạm vi phân tích” + disclaimer; không dùng từ “an toàn”.
* `INSUFFICIENT_EVIDENCE`: hiển thị risk label/basis type và dòng “Chưa đủ căn cứ pháp lý trong kho luật”; không hiện severity badge.
* Mỗi clause có một span partition không chồng lấn. Nếu một clause có nhiều risk label thì dùng **một highlight** cho clause, detail panel hiển thị nhiều label; không tạo highlight chồng lên cùng span.
* API offset là Unicode code point. JavaScript phải tạo map code-point -> UTF-16 index trước khi `slice`/render DOM nếu text chứa ký tự ngoài BMP.
* Catalog message tiếng Việt tối thiểu nằm ở Phụ lục E; technical code không hiển thị một mình cho người dùng.
