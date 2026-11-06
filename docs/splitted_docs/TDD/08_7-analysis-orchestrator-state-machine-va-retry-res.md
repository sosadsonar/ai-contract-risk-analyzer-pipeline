<!-- nguồn: TDD_AI_Labor_Contract_Risk_Analyzer_v0.3.md | mục: 7. Analysis Orchestrator, state machine và retry/resume | 3376 ký tự | trước: 07_6-domain-model-va-json-schema.md | sau: 09_8-document-processing-va-canonical-text.md -->

# 7. Analysis Orchestrator, state machine và retry/resume

## 7.1 Runtime stage order

```text
UPLOAD
  -> EXTRACTION
  -> SCOPE_PRECHECK
  -> PII_MASKING
  -> SEGMENTATION
  -> CLAUSE_GRAPH
  -> [status PROCESSING]
  -> CLAUSE_CLASSIFICATION (LLM #1)
  -> LEGAL_RETRIEVAL (baseline + optional Data Graph)
  -> RISK_ANALYSIS (LLM #2, optional Clause Graph context)
  -> CITATION_VALIDATION
  -> ASSEMBLY
  -> COMPLETED
```

VALIDATING bao phủ EXTRACTION đến CLAUSE_GRAPH. PROCESSING bắt đầu ngay trước LLM #1. Orchestrator là nơi duy nhất đổi state.

State transition chi tiết:

```text
UPLOADED -> VALIDATING -> REJECTED
                    |-> FAILED          (local/internal failure)
                    |-> PROCESSING -> COMPLETED
                                  |-> FAILED

FAILED --manual retry--> VALIDATING   nếu failed_stage thuộc local validating stages
FAILED --manual retry--> PROCESSING   nếu failed_stage thuộc processing stages
COMPLETED | FAILED | REJECTED -> EXPIRED
```

Điểm retry target trên cụ thể hóa FR-21 “resume từ stage lỗi”; không thay semantics REJECTED/FAILED của SRS.

## 7.2 Typed result và exception mapping

| Tầng | Kiểu lỗi | Mapping |
|---|---|---|
| Input/local validation | ValidationReject(code) | REJECTED với code SRS 6.2 |
| LLM client timeout/network/retryable provider | AiTimeout/AiProviderError | FAILED / AI_TIMEOUT hoặc AI_PROVIDER_ERROR |
| Structured output/schema | AiOutputInvalid | FAILED / AI_OUTPUT_INVALID sau 1 retry |
| Local runtime | PipelineInternalError | FAILED / INTERNAL_ERROR |
| Corpus startup/reload | LegalCorpusConflict | Fail fast / LEGAL_CORPUS_CONFLICT |

## 7.3 Stage resume (chỉ giai đoạn AI)

Mỗi StageArtifact in-memory lưu status và output của stage AI. Artifact dùng lại được khi bộ version pin (§6.4) lưu trong phiên khớp bộ hiện tại; phiên nằm trong RAM của một process nên file, vai trò và analysis_date không đổi trong phiên, vì vậy không dùng SHA-256 chuỗi hash upstream. Retry giai đoạn VALIDATING luôn chạy lại từ EXTRACTION, không resume. Manual retry của giai đoạn PROCESSING chạy lại từ stage AI lỗi. Nếu stage resume bị cắt (cut item 2), chạy lại giai đoạn PROCESSING từ đầu, vẫn giữ giới hạn 2 manual retries.

## 7.4 Processing lease, concurrency và cancellation

* Dùng non-blocking processing lease/semaphore capacity=1. POST Create và POST Retry đều phải `try_acquire()` **ngay ở request entry** trước khi tạo/schedule work; không chờ queue.
* Create gate fail -> SYSTEM_BUSY và không tạo session. Retry gate fail -> SYSTEM_BUSY, không đổi state/counter.
* Lease owner là `session_id`; giữ trong toàn bộ VALIDATING/PROCESSING và release duy nhất trong `finally` khi tới COMPLETED/FAILED/REJECTED/EXPIRED/cancel.
* FAILED không giữ lease. Vì vậy retry phải acquire lại. Chỉ sau khi acquire mới tăng `manual_retry_count` atomically.
* LLM parallelism chỉ giữa batch của cùng session.
* End Session set cancellation flag, cancel outstanding provider tasks; stage kiểm tra cancel giữa batches.
* CPU-heavy extraction/regex chạy threadpool, không block event loop/polling.

## 7.5 Race-condition tests

Bắt buộc có test barrier cho hai Create đồng thời để chứng minh chỉ một request acquire lease. Có test Retry trong khi session khác đang chạy: trả SYSTEM_BUSY, retry_count không tăng. Có test End Session và provider callback race: callback sau cleanup không được resurrect session.
