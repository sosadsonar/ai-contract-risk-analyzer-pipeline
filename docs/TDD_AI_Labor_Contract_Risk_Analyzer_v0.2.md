**TECHNICAL DESIGN DOCUMENT**

**AI Labor Contract Risk Analyzer**

TDD phiên bản 0.2 (Draft)

Cơ sở: BRD 0.5 \+ SRS 1.3 \+ SDD 0.1

Ngày: 12/10/2026

*Mục tiêu: khóa các chi tiết kỹ thuật đủ để backend, AI pipeline, frontend và evaluation harness triển khai nhất quán.*

# **Kiểm soát tài liệu**

| Mục | Giá trị |
| :---- | :---- |
| Tên tài liệu | Technical Design Document \- AI Labor Contract Risk Analyzer |
| Phiên bản | 0.2 \- Draft |
| Ngày | 12/10/2026 |
| Nguồn yêu cầu | BRD 0.5 (draft), SRS 1.3, SDD 0.1 |
| Phạm vi | API contract, JSON Schema, module/class, thuật toán local, graph, legal retrieval, LLM adapter, cấu hình, test và evaluation artifacts |
| Không thay đổi | Business scope, pipeline invariant, state semantics, privacy boundary, closed-corpus rule, chỉ số nghiệm thu trong BRD |
| Trạng thái | Draft kỹ thuật; các giá trị cấu hình ghi “tune trên D1” được phép đổi mà không đổi API/schema semantics |

## **Thay đổi chính trong 0.2**

Bản 0.2 rà soát lại TDD 0.1 theo BRD 0.5, SRS 1.3, SDD 0.1 và review kỹ thuật. Các thay đổi chính: thống nhất upload bất đồng bộ và trạng thái REJECTED; bổ sung basis type ở final view nhưng giữ `risk_labels` của SRS; sửa retry/processing lock; làm M8 graph on/off công bằng; khóa partition clause không chồng lấn; tăng kiểm tra PDF font cũ; sửa Clause Graph REFERS_TO; tối ưu payload/token; bổ sung frontend contract, fixture format, privacy/BL-1/annotation metrics; và khóa deployment một worker cho session store in-memory.

Các đề xuất đòi hỏi thay đổi SRS (ví dụ thêm trường `related_clause_ids` vào RiskResult) **không được tự ý đưa vào product schema**. TDD 0.2 dùng diagnostic/evaluation trace để chứng minh Clause Graph đã được dùng, đồng thời ghi mục cần backport SRS ở §21.

## **Quy tắc ưu tiên nguồn**

* BRD 0.5 là nguồn nghiệp vụ và Evaluation Plan. TDD không thay đổi phạm vi, business rule hay ngưỡng M1-M8/PII.  
* SRS 1.3 là nguồn bắt buộc cho FR/NFR, entity tối thiểu, invariant, state và error code.  
* SDD 0.1 là nguồn kiến trúc: modular monolith, session tạm thời, Data Graph như lớp mở rộng, Clause Graph như Context Resolver, hai LLM call bắt buộc.  
* TDD chỉ khóa chi tiết còn mở ở SDD §16 và SRS OI-02..OI-09/OI-12. Nếu TDD mâu thuẫn BRD/SRS, BRD/SRS thắng và TDD phải sửa.

| Lưu ý trạng thái: BRD 0.5, SRS 1.3 và SDD 0.1 đều đang ở trạng thái draft/chờ duyệt ở một số quyết định. TDD này giữ nguyên các quyết định draft đó thay vì tự đổi phạm vi. |
| :---- |

## **Mục lục logic**

* 1\. Mục đích, phạm vi và invariant kỹ thuật  
* 2\. Các quyết định kỹ thuật TDD  
* 3\. Stack triển khai và cấu trúc repository  
* 4\. Configuration, secret và startup  
* 5\. HTTP API Contract  
* 6\. Domain model và JSON Schema  
* 7\. Analysis Orchestrator, state machine và retry/resume  
* 8\. Document Processing và canonical text  
* 9\. Scope Precheck  
* 10\. PII Masking  
* 11\. Clause Segmentation  
* 12\. Clause Graph và Context Resolver  
* 13\. Clause Classification LLM  
* 14\. Legal Corpus, Baseline Retrieval và Data Graph  
* 15\. Risk Analysis, citation validation và assembly  
* 16\. Export report  
* 17\. Logging, quota, rate limit, retention và security  
* 18\. Evaluation Harness và gold format  
* 19\. Test strategy  
* 20\. Traceability và kế hoạch migration codebase  
* 21\. Open items / giới hạn đã biết  
* Phụ lục A-E: schema mẫu, env, prompt contract, checklist và UI message catalog

# **1\. Mục đích, phạm vi và invariant kỹ thuật**

TDD chuyển SRS 1.3 và SDD 0.1 thành các hợp đồng kỹ thuật đủ cụ thể để triển khai và kiểm thử. Các chi tiết dưới đây ưu tiên tính đơn giản, truy vết và khả năng hoàn thành trong 8 tuần xây dựng; không tối ưu theo tiêu chuẩn production.

## **1.1 Invariant không được phá**

* Canonical text là nguồn duy nhất cho quote, span, highlight và export quote.  
* PII masking chạy trên toàn canonical\_text trước segmentation; len(masked\_text) \== len(canonical\_text).  
* canonical\_text\[start\_char:end\_char\] \== original\_text cho mọi clause; ranh giới không nằm trong placeholder.  
* Chỉ masked text được phép ra khỏi trusted backend tới Gemini; LLM không sinh hoặc sửa quote/span.  
* Mọi output AI join bằng clause\_id. Backend sở hữu state, span, citation validation và final assembly.  
* Legal retrieval chạy local; citation chỉ thuộc candidate list, closed corpus và phiên bản hiệu lực tại analysis\_date.  
* INSUFFICIENT\_EVIDENCE \=\> citation\_ids rỗng và severity \= null.  
* Clause Graph chỉ chứa clause\_id \+ edge\_type; không chứa contract text và không thay đổi segmentation/span.  
* Nội dung hợp đồng/session không lưu bền vững; restart backend làm mất session content.  
* Một phiên VALIDATING/PROCESSING tại một thời điểm; REJECTED không retry, FAILED retry thủ công tối đa 2 lần.

## **1.2 Non-goals của TDD**

* Không thêm chatbot, user account, missing-clause detection, OCR, mobile app, fine-tune/self-host model.  
* Không dùng graph database hoặc microservice cho demo.  
* Không đưa advice/suggestion sửa điều khoản vào prompt, API response hay export.  
* Không định nghĩa lại M1-M8, BL-1 hay ngưỡng PII; TDD chỉ cung cấp artifact để đo các chỉ số đó.

# **2\. Các quyết định kỹ thuật TDD**

| ID | Quyết định | Lý do / nguồn |
| :---- | :---- | :---- |
| TDD-01 | Python backend giữ kiến trúc modular monolith; FastAPI làm HTTP layer, Pydantic v2 làm runtime schema/serialization. | Khớp SDD-01; API/schema rõ ràng. |
| TDD-02 | Session content lưu trong `InMemorySessionStore`; file upload chỉ dùng temp storage theo session khi parser cần path và bị xóa theo cleanup. | NFR-DATA-04/SDD-02. |
| TDD-03 | Operational metadata dùng SQLite qua `sqlite3`, chỉ gồm RunLog, usage/quota, rate counter và EXPIRED tombstone; cấm contract content/PII. | Giữ metadata qua restart mà không đưa dữ liệu hợp đồng vào DB. |
| TDD-04 | PDF extraction dùng PyMuPDF; DOCX dùng python-docx + lxml/OOXML cho numbering, tracked changes, textbox. | FR-08. |
| TDD-05 | PII placeholder giữ đúng số Unicode code point. Tag loại PII dùng ASCII; phần đệm dùng `_` lặp lại thay vì ký tự block để giảm token. | Khóa OI-02, giữ span và giảm token. |
| TDD-06 | Segmentation mặc định rule-based; structural heading -> paragraph fallback; baseline không dùng LLM semantic segmentation. | DEC-18; cut item 3. |
| TDD-07 | Clause Graph context tối đa 3 clause và 6.000 code point masked/context cho mỗi target; ưu tiên REFERS_TO -> PARENT_OF -> NEXT. `CLAUSE_GRAPH_ENABLED=true` ở demo; chỉ được tắt trong dev/eval/test. | SDD §6.2, FR-31. |
| TDD-08 | Legal corpus là JSONL/YAML versioned; `citation_id` deterministic từ `document_id` + provision path; index fail-fast. | FR-24, FR-30. |
| TDD-09 | Baseline retrieval = weighted label map + BM25 lexical; embedding disabled mặc định và chỉ cân nhắc sau D2 nếu M8 chưa đạt. | SDD-03. |
| TDD-10 | Baseline luôn tạo `final_k` candidate. Khi graph bật, top `seed_k` là seed mở rộng 1 hop; graph-off và graph-on đều trả cùng `final_k` để EV-08/M8 so sánh công bằng. | FR-12, FR-30, EV-08. |
| TDD-11 | Graph ranking seed-first cho top seed; phần còn lại merge baseline backup với graph-only neighbor. Hướng cạnh/cap neighbor được khóa ở §14.6; trọng số tune trên D1/D2. | SDD-05; review fairness/fan-out. |
| TDD-12 | Clause classification batch_size=20, risk batch_size=6, `llm_parallelism=2` là default dev; phải benchmark D1 trước MS-2. | FR-28, NFR-PERF-01. |
| TDD-13 | Gemini timeout 30s; auto-retry tối đa 1 lần chỉ cho timeout/network/429/5xx và output-schema invalid; 400/401/403 không auto-retry. | FR-21/NFR-REL-02; kiểm soát cost. |
| TDD-14 | Daily call quota là config bắt buộc trước demo, **không khóa số 120**. Giá trị được chốt từ call/token/cost đo trên D1 và ngân sách vận hành $5; IP upload limit mặc định 5 requests/10 phút. | FR-27/NFR-COST-02. |
| TDD-15 | EXPIRED tombstone lưu 24h trong operational metadata, sau đó `SESSION_NOT_FOUND`. | SRS OI-06 default. |
| TDD-16 | Stage resume dùng fingerprint SHA-256 của upstream hashes + version pins + config version; mismatch -> chạy lại từ stage đầu cần thiết. | FR-21/NFR-REL-03. |
| TDD-17 | Mọi schema có `schema_version`; output AI ghi model/prompt/taxonomy/rubric/corpus/extraction version theo FR-29. | BR-05c/FR-29. |
| TDD-18 | Export DOCX ưu tiên; PDF dùng cùng ReportModel nếu feature còn giữ. Report chứa disclaimer **và data notice**; file không lưu sau session. | FR-22, FR-25. |
| TDD-19 | Evaluation harness gọi shared pipeline trực tiếp, không dùng HTTP/session runtime quota/rate-limit; vẫn có ledger riêng cho chi phí đánh giá. | EV-01, ngân sách $15 đánh giá. |
| TDD-20 | Prompt khóa format/policy/version; few-shot là artifact versioned; không tuning trên T1/T2. Gemini dùng provider structured output/response schema. | EV-07, FR-29, SRS C-07. |
| TDD-21 | Demo deploy đúng **1 backend worker/process**, không autoscale/serverless. CPU-bound extraction/regex chạy bằng threadpool để event loop vẫn phục vụ polling. | NFR-DATA-04, FR-26, NFR-PERF-02, SRS C-05. |
| TDD-22 | `start_char/end_char` và mọi span backend/API tính theo Unicode code point sau NFC; frontend phải chuyển code-point offset sang UTF-16 index khi thao tác chuỗi JavaScript/DOM. | Làm rõ invariant cross-runtime. |
| TDD-23 | Product `RiskResult` giữ `risk_labels[]` theo SRS; backend derive `risk_basis[] = [{label,basis_type}]` từ risk taxonomy cho final API/UI/export. LLM không tự khai `basis_type`. | Giữ tương thích SRS 4.1/FR-13 và tránh mất loại rủi ro. |
| TDD-24 | Clause Graph không thêm field product mới chưa có trong SRS. Dev/eval sinh `ContextResolutionTrace` để chứng minh related clauses nào đã được đưa vào Risk LLM. | Nghiệm thu FR-31 mà không tự đổi SRS. |
| TDD-25 | `LLMProvider` abstraction cho phép Gemini paid ở demo/eval và optional local/dev adapter chỉ với dữ liệu de-identified; product path không tự host model. | NFR-SEC-06, SRS C-07. |

| Các giá trị batch/rate/graph weight/neighbor cap là default kỹ thuật và có thể tune **chỉ trên D1/D2 trước khi khóa demo**. Daily call quota phải có số đo cost model trước demo; không được tune trên T1/T2. |
| :---- |

# **3\. Stack triển khai và cấu trúc repository**

## **3.1 Stack đề xuất**

| Layer | Công nghệ / thư viện | Vai trò |
| :---- | :---- | :---- |
| Runtime | Python 3.12 | Một runtime chung cho backend và ai\_pipeline. |
| HTTP API | FastAPI \+ Uvicorn | 6 operation bắt buộc, multipart upload, streaming export. |
| Schema | Pydantic v2 \+ JSON Schema | Validate API và structured output; sinh schema versioned. |
| PDF | PyMuPDF | Extraction, page count, block/coordinate reading. |
| DOCX | python-docx \+ lxml | Paragraph/table \+ OOXML numbering/tracked change/textbox. |
| Unicode | unicodedata (stdlib) | NFC normalization. |
| Lexical retrieval | rank-bm25 | BM25 trên legal corpus; deterministic, local. |
| Graph | dict/list adjacency index | Không graph DB; 1-hop expansion. |
| Operational metadata | sqlite3 (stdlib) | RunLog/quota/rate/tombstone; không contract content. |
| Export | python-docx; PDF renderer tùy môi trường | DOCX first, PDF cut item. |
| Test | pytest \+ pytest-asyncio | Unit/integration/contract/eval fixtures. |
| Eval | Python CLI + JSON/CSV | M1-M8, privacy, annotation kappa, BL-1 và graph on/off. |

## **3.2 Cấu trúc package**

```text
backend/
  app/
    main.py
    api/
      routes/sessions.py
      deps.py
      errors.py
    core/
      config.py
      enums.py
      clock.py
      security.py
    domain/
      models.py
      schemas.py
      errors.py
    session/
      store.py
      cleanup.py
      lock.py
      orchestrator.py
    document/
      extractor.py
      pdf_extractor.py
      docx_extractor.py
      canonicalizer.py
      quality.py
      scope_precheck.py
    privacy/
      pii_types.py
      detector.py
      masker.py
    clause/
      segmenter.py
      structure_parser.py
      graph_builder.py
      context_resolver.py
      taxonomy.py
    ai/
      provider.py
      gemini_client.py
      dev_local_client.py       # optional dev only
      clause_adapter.py
      risk_adapter.py
      prompts/
        clause_v1.py
        risk_v1.py
    legal/
      corpus_loader.py
      corpus_validator.py
      citation_id.py
      baseline_retriever.py
      data_graph.py
      citation_validator.py
    result/
      assembler.py
      exporter.py
    ops/
      runlog.py
      quota.py
      rate_limit.py
      metadata_db.py

ai_pipeline/
  schemas/
    extraction_v1.json
    masking_v1.json
    segmentation_v1.json
    clause_output_v3.json
    retrieval_v1.json
    risk_output_v1.json
    final_result_v1.json
  evaluation/
    runner.py
    metrics/
    gold/

data/
  legal_corpus/
    manifest.yaml
    provisions.jsonl
    edges.jsonl
    edge_suggestions.jsonl
    label_map.yaml
  docs/
    clause_taxonomy/
    risk_taxonomy/
    severity_rubric/

tests/
  unit/
  integration/
  contract/
  fixtures/
```

Không tạo package explanation AI riêng vì explanation nằm trong Risk Analysis LLM call #2. Không có `contract_id/analysis_id`. Frontend framework không bị TDD khóa; contract tích hợp bắt buộc nằm ở §5.9.

# **4\. Configuration, secret và startup**

## **4.1 Biến cấu hình**

| Tên | Kiểu | Default | Ghi chú |
| :---- | :---- | :---- | :---- |
| APP_ENV | `dev`, `demo`, `eval` | dev | `eval` bypass runtime quota/rate-limit, nhưng ghi eval cost ledger. |
| GEMINI_API_KEY | secret | - | Bắt buộc ở demo/eval; không log. |
| GEMINI_MODEL_ID | string | - | Bắt buộc ở demo/eval; startup fail nếu thiếu. |
| DEV_LLM_PROVIDER | `gemini` or `local` | gemini | `local` chỉ ở dev với dữ liệu de-identified. |
| LLM_TIMEOUT_SECONDS | int | 30 | Theo NFR-REL-02. |
| LLM_AUTO_RETRY | int | 1 | Không vượt 1. |
| CLAUSE_BATCH_SIZE | int | 20 | Tune D1. |
| RISK_BATCH_SIZE | int | 6 | Tune D1. |
| LLM_PARALLELISM | int | 2 | Trong một session; benchmark D1. |
| MAX_PDF_PAGES | int | 30 | FR-04. |
| MAX_UPLOAD_MB | int | 10 | FR-04. |
| MAX_DOCX_CHARS | int | 100000 | FR-04. |
| MAX_CLAUSES | int | 150 | FR-09. |
| SESSION_TTL_MINUTES | int | 60 | FR-23. |
| EXPIRED_TOMBSTONE_HOURS | int | 24 | TDD-15. |
| DAILY_LLM_CALL_QUOTA | int | **required in demo** | Chốt từ D1 + cost model; không dùng default 120. |
| SESSION_CALL_RESERVE | int | **required in demo** | p95 planned calls/contract trên D1, dùng admission control. |
| RATE_LIMIT_UPLOADS | int | 5 | Default, tune trước demo. |
| RATE_LIMIT_WINDOW_SECONDS | int | 600 | 10 phút. |
| DATA_GRAPH_ENABLED | bool | true | EV-08 chạy true/false. |
| CLAUSE_GRAPH_ENABLED | bool | true | Demo bắt buộc true; false chỉ dev/eval/test. |
| RETRIEVAL_SEED_K | int | 3 | Top baseline seeds để mở rộng graph. |
| RETRIEVAL_FINAL_K | int | 8 | Cả graph on/off đều trả tối đa 8. |
| GRAPH_MAX_NEIGHBORS_PER_SEED | int | 4 | Chống fan-out. |
| GRAPH_MAX_CHILDREN_PER_SEED | int | 2 | Cap PARENT_OF child expansion. |
| CLAUSE_GRAPH_MAX_RELATED | int | 3 | TDD-07. |
| CLAUSE_GRAPH_MAX_CONTEXT_CHARS | int | 6000 | Unicode code point. |
| SCOPE_TITLE_SCAN_CHARS | int | 1000 | Strong-title chỉ tính ở vùng đầu. |
| TEMPERATURE | float | 0.0 | Cố định/reproducible. |

## **4.2 Startup sequence**

1. Load config; validate numeric limits. Ở `demo/eval`, thiếu Gemini model/key hoặc daily quota/session reserve thì startup fail. Ở `dev`, local provider chỉ được phép với dữ liệu de-identified.
2. Load clause taxonomy, risk taxonomy (gồm `basis_type`), severity rubric; validate version metadata.
3. Load legal corpus manifest/provisions/edges; validate citation IDs, version overlap, edge endpoints, PARENT_OF acyclic.
4. Build BM25 index + weighted label map; build Data Graph adjacency index nếu enabled.
5. Open operational metadata SQLite; migration chỉ cho metadata.
6. Khởi tạo InMemorySessionStore, cleanup scheduler và non-blocking global processing lease capacity=1.
7. Khởi tạo threadpool cho PyMuPDF/DOCX parsing, regex/CPU-heavy local preprocessing.
8. Chỉ expose readiness=true sau khi thành công. `LEGAL_CORPUS_CONFLICT` làm service fail-fast.

## **4.3 Deployment constraint**

Demo chạy **một Uvicorn worker/process duy nhất**. Không dùng multiple worker, autoscale hoặc serverless scale-out vì session store và processing lease là in-memory/process-local. Nếu sau này cần nhiều worker thì phải đổi SDD/TDD sang shared session/lock store; ngoài phạm vi demo.

# **5\. HTTP API Contract**

## **5.1 Quy ước chung**

* Base path: `/api/v1`. JSON UTF-8; upload dùng `multipart/form-data`.
* `session_id` là UUID v4 opaque.
* Error body: `{error:{code,message,retryable,details?}}`, message tiếng Việt.
* SRS 6.2 là **tập mã lỗi tối thiểu**. TDD định nghĩa thêm một số API-state code ở §5.8; chúng không tạo state mới và nên được backport vào SRS để truy vết.
* Polling Get Status không cập nhật `last_activity_at`. Get Result, Retry, Export, End Session là user activity.
* Không trả canonical/masked text trong error/log. Get Result chỉ trả canonical text khi COMPLETED.
* Không authentication trong demo; deployment dùng HTTPS.

## **5.2 POST /api/v1/sessions - Create/Upload**

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
| :---- | :---- | :---- |
| Thiếu role | 400 | ROLE_REQUIRED |
| Processing lease đang bận | 409 | SYSTEM_BUSY |
| Không đủ quota reservation cho session mới | 429 | QUOTA_EXCEEDED |
| Vượt rate theo IP | 429 | RATE_LIMITED |

Các mã `UNSUPPORTED_FILE_TYPE`, `FILE_TOO_LARGE`, `PDF_PAGE_LIMIT_EXCEEDED`, `DOCX_TEXT_LIMIT_EXCEEDED`, `NO_EXTRACTABLE_TEXT`, `UNSUPPORTED_TEXT_ENCODING`, `NOT_LABOR_CONTRACT`, `TOO_MANY_CLAUSES` là **REJECTED của session**. Chúng không được trả như lỗi đồng bộ của POST sau khi session đã tạo.

Nếu upload stream bị ngắt trước khi file được nhận đủ, đây là lỗi pipeline/input của session và được map theo typed error phù hợp; processing lease vẫn release trong `finally`.

## **5.3 GET /api/v1/sessions/{session_id}/status**

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

## **5.4 GET /api/v1/sessions/{session_id}/result**

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
     "risk_labels":["PROBATION_WAGE_BELOW_MINIMUM"],
     "risk_basis":[{"label":"PROBATION_WAGE_BELOW_MINIMUM","basis_type":"LEGAL_VIOLATION"}],
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

`risk_basis` do backend derive từ risk taxonomy sau khi validate `risk_labels`; LLM không được tự khai `basis_type`.

## **5.5 POST /api/v1/sessions/{session_id}/retry**

Chỉ status=FAILED và `manual_retry_count < 2`. Retry phải `try_acquire()` processing lease **trước** khi tăng counter. Nếu lease bận: `409 SYSTEM_BUSY`, counter không tăng. Nếu state không phải FAILED: `409 INVALID_SESSION_STATE`. Chỉ retry thứ 3 mới dùng `RETRY_LIMIT_EXCEEDED`.

Sau khi acquire lease, Orchestrator xác định `failed_stage`: lỗi ở local stage trước LLM #1 -> state quay lại VALIDATING; lỗi ở PROCESSING -> state PROCESSING. Resume từ stage lỗi nếu fingerprint hợp lệ; nếu cut stage-resume thì chạy lại từ đầu.

## **5.6 GET /api/v1/sessions/{session_id}/export?format=docx|pdf**

Chỉ COMPLETED. Server build report in-memory/temp, stream file và xóa trong `finally`. Nếu PDF đã bị cắt, `format=pdf` trả `501 FEATURE_NOT_ENABLED`; DOCX vẫn bắt buộc.

## **5.7 DELETE /api/v1/sessions/{session_id}**

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

## **5.8 ErrorResponse và API-state code**

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
| :---- | :---- | :---- |
| INVALID_SESSION_STATE | Retry/operation không hợp lệ theo state | Không dùng thay RETRY_LIMIT_EXCEEDED. |
| SESSION_NOT_READY | Get Result/Export khi VALIDATING/PROCESSING/FAILED | State không đổi. |
| SESSION_REJECTED | Get Result/Export khi REJECTED | Chi tiết nguyên nhân lấy từ status.error_code. |
| SESSION_EXPIRED | Get Result/Export khi còn tombstone EXPIRED | HTTP 410. |
| FEATURE_NOT_ENABLED | PDF export bị cắt | Chỉ feature cut. |

Các code trên là chi tiết API của TDD vì SRS 6.2 ghi “mã lỗi tối thiểu”. Đề xuất cập nhật ngược SRS để traceability đầy đủ.

## **5.9 Frontend integration contract**

* Sau 201, frontend bắt đầu polling status sau 500 ms; trong VALIDATING/PROCESSING poll mỗi 1,5 giây. Sau 60 giây có thể giảm xuống 2,5 giây. Dừng polling ở COMPLETED/FAILED/REJECTED/EXPIRED. Mục tiêu UI hiển thị VALIDATING/PROCESSING trong <=2 giây theo NFR-PERF-02.
* REJECTED: hiển thị thông báo theo `error_code`; không hiện nút Retry, chỉ cho mở phiên mới.
* FAILED: hiển thị lỗi + nút Retry khi `manual_retry_count < 2`; retry có thể trả SYSTEM_BUSY.
* COMPLETED + không risk: hiển thị “Không phát hiện rủi ro trong phạm vi phân tích” + disclaimer; không dùng từ “an toàn”.
* `INSUFFICIENT_EVIDENCE`: hiển thị risk label/basis type và dòng “Chưa đủ căn cứ pháp lý trong kho luật”; không hiện severity badge.
* Mỗi clause có một span partition không chồng lấn. Nếu một clause có nhiều risk label thì dùng **một highlight** cho clause, detail panel hiển thị nhiều label; không tạo highlight chồng lên cùng span.
* API offset là Unicode code point. JavaScript phải tạo map code-point -> UTF-16 index trước khi `slice`/render DOM nếu text chứa ký tự ngoài BMP.
* Catalog message tiếng Việt tối thiểu nằm ở Phụ lục E; technical code không hiển thị một mình cho người dùng.

# **6\. Domain model và JSON Schema**

## **6.1 Enum chuẩn**

| Enum | Giá trị |
| :---- | :---- |
| Role | EMPLOYEE, EMPLOYER |
| SessionStatus | UPLOADED, VALIDATING, REJECTED, PROCESSING, COMPLETED, FAILED, EXPIRED |
| Stage | UPLOAD, EXTRACTION, SCOPE_PRECHECK, PII_MASKING, SEGMENTATION, CLAUSE_GRAPH, CLAUSE_CLASSIFICATION, LEGAL_RETRIEVAL, RISK_ANALYSIS, CITATION_VALIDATION, ASSEMBLY, EXPORT |
| Severity | HIGH, MEDIUM, LOW, null |
| EvidenceStatus | SUPPORTED, INSUFFICIENT_EVIDENCE |
| BasisType | LEGAL_VIOLATION, UNFAVORABLE, AMBIGUOUS |
| LegalEdgeType | PARENT_OF, REFERS_TO, GUIDES |
| ClauseEdgeType | NEXT, PARENT_OF, REFERS_TO |

## **6.2 Session aggregate**

```python
class Session:
    session_id: UUID
    role: Role
    status: SessionStatus
    current_stage: Stage | None
    failed_stage: Stage | None
    created_at: datetime
    last_activity_at: datetime
    manual_retry_count: int
    filename: str
    analysis_date: date
    extraction_version: str | None
    canonical_text: str | None
    masked_text: str | None
    pii_spans: list[PiiSpan]              # start/end/type only; no original value
    clauses: list[Clause]
    clause_graph: ClauseGraph | None
    clause_classification_outputs: dict[str, ClauseClassOutput]
    legal_candidates: dict[str, list[LegalCandidate]]
    risk_results: list[RiskResult]
    version_pins: VersionPins
    stage_cache: dict[Stage, StageArtifact]
    last_error: ErrorInfo | None
    active_tasks: set[TaskHandle]
```

Session object chỉ ở memory. `pii_spans` không lưu original PII value/reverse mapping. Processing lease là resource của Orchestrator, không serialize trong Session content.

## **6.3 Clause và RiskResult**

```json
Clause {
  "clause_id": "cl_0001",
  "original_text": "...",
  "start_char": 0,
  "end_char": 128,
  "clause_labels": ["COMPENSATION_BENEFITS"]
}

RiskResult {
  "clause_id": "cl_0001",
  "role": "EMPLOYEE",
  "risk_labels": ["PROBATION_WAGE_BELOW_MINIMUM"],
  "risk_basis": [
    {"label":"PROBATION_WAGE_BELOW_MINIMUM", "basis_type":"LEGAL_VIOLATION"}
  ],
  "severity": "HIGH",
  "explanation": "...",
  "evidence_status": "SUPPORTED",
  "citation_ids": ["BLLD2019:art26"],
  "version_pins": {...}
}
```

`risk_labels[]` là field nguồn theo SRS. `risk_basis[]` là field **derived by backend** từ risk taxonomy và phải one-to-one với `risk_labels`; không nằm trong AI output. Severity/explanation/citation vẫn ở cấp clause đúng entity tối thiểu SRS. Nếu nhóm muốn severity riêng cho từng label thì phải sửa SRS trước.

## **6.4 VersionPins**

```json
{
  "extraction_version": "extract_v1.1",
  "clause_taxonomy_version": "clause_taxonomy_v03",
  "risk_taxonomy_version": "risk_taxonomy_v01",
  "severity_rubric_version": "severity_v01",
  "corpus_version": "legal_corpus_2026-10-12",
  "data_graph_version": "legal_graph_2026-10-12",
  "clause_prompt_version": "clause_prompt_v1",
  "risk_prompt_version": "risk_prompt_v1",
  "model_id": "<configured-gemini-flash-model>",
  "temperature": 0.0,
  "app_commit": "<git-sha>"
}
```

> **Đối chiếu data (17/10/2026):** `clause_taxonomy_version` là phiên bản taxonomy **nguồn của data** (hiện `clause_taxonomy_v03`, 12 nhãn). Revision định nghĩa dùng trong prompt ở code (`TAXONOMY_VERSION = "v04"` trong `taxonomy.py`, sửa ranh giới nhãn, không thêm/bớt nhãn) được ghi qua `clause_prompt_version` **[Đề xuất]**; không thêm trường mới vào VersionPins vì FR-29 chưa đổi. Nhãn trong ví dụ JSON của TDD là minh họa và phải thuộc 12 nhãn của taxonomy.

## **6.5 Stage schema bắt buộc**

| Schema | Trường chính |
| :---- | :---- |
| extraction_v1 | filename, role, extraction_version, canonical_text, page_count?, char_count |
| masking_v1 | schema_version, masked_text, pii_spans[{type,start,end}], masking_version |
| segmentation_v1 | schema_version, clauses[{clause_id,original_text,start_char,end_char,structure}], segmentation_version |
| clause_output_v3 | schema_version, items[{clause_id,clause_labels[1..3]}], model_id,prompt_version,taxonomy_version |
| retrieval_v1 | per_clause[{clause_id,candidates[]}], corpus_version,data_graph_version,graph_enabled |
| risk_output_v1 | items[{clause_id,risk_labels,severity,explanation,evidence_status,citation_ids}], version pins |
| final_result_v1 | offset_unit, session/role/date, canonical_text, clauses, risks(+derived risk_basis), citations, disclaimer, data_notice, version_pins |

`ContextResolutionTrace` là diagnostic artifact cho dev/eval, không phải field bắt buộc của RiskResult/API product.

## **6.6 Validation sau mỗi stage**

* Extraction: NFC, canonical non-empty, limits, quality/legacy-font heuristic pass.
* Masking: length equality theo Unicode code point; PII span valid/non-overlap; no reverse mapping.
* Segmentation: clause IDs unique; spans sorted, **non-overlapping partition**; exact substring invariant; no boundary in PII; <=150.
* Clause Classification: every requested clause exactly once; 1..3 labels từ taxonomy; không span/quote; request không có role.
* Retrieval: candidate exists/effective; count <= final_k; graph on/off cùng final_k.
* Risk: labels valid; citation subset candidates; severity/evidence invariant; advice/citation-mention sanitizer pass.
* Assembly: derive `risk_basis` từ taxonomy; no risk without clause; quote/span chỉ từ canonical Clause; add `offset_unit=unicode_code_point`.

# **7\. Analysis Orchestrator, state machine và retry/resume**

## **7.1 Runtime stage order**

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

## **7.2 Typed result và exception mapping**

| Tầng | Kiểu lỗi | Mapping |
| :---- | :---- | :---- |
| Input/local validation | ValidationReject(code) | REJECTED với code SRS 6.2 |
| LLM client timeout/network/retryable provider | AiTimeout/AiProviderError | FAILED / AI_TIMEOUT hoặc AI_PROVIDER_ERROR |
| Structured output/schema | AiOutputInvalid | FAILED / AI_OUTPUT_INVALID sau 1 retry |
| Local runtime | PipelineInternalError | FAILED / INTERNAL_ERROR |
| Corpus startup/reload | LegalCorpusConflict | Fail fast / LEGAL_CORPUS_CONFLICT |

## **7.3 Stage resume fingerprint**

Mỗi StageArtifact in-memory lưu status, output và fingerprint. Fingerprint dùng canonical JSON + SHA-256; content hash không ghi vào persistent RunLog.

```text
fingerprint(stage) = SHA256(
  stage_name
  + upstream_artifact_hashes
  + role
  + analysis_date
  + relevant extraction/taxonomy/corpus/prompt/model versions
  + stage-specific config version
)
```

Manual retry tìm `failed_stage` và chỉ reuse artifact có fingerprint còn hợp lệ. Nếu stage resume bị cắt, chạy lại pipeline từ đầu nhưng giữ giới hạn 2 manual retries.

## **7.4 Processing lease, concurrency và cancellation**

* Dùng non-blocking processing lease/semaphore capacity=1. POST Create và POST Retry đều phải `try_acquire()` **ngay ở request entry** trước khi tạo/schedule work; không chờ queue.
* Create gate fail -> SYSTEM_BUSY và không tạo session. Retry gate fail -> SYSTEM_BUSY, không đổi state/counter.
* Lease owner là `session_id`; giữ trong toàn bộ VALIDATING/PROCESSING và release duy nhất trong `finally` khi tới COMPLETED/FAILED/REJECTED/EXPIRED/cancel.
* FAILED không giữ lease. Vì vậy retry phải acquire lại. Chỉ sau khi acquire mới tăng `manual_retry_count` atomically.
* LLM parallelism chỉ giữa batch của cùng session.
* End Session set cancellation flag, cancel outstanding provider tasks; stage kiểm tra cancel giữa batches.
* CPU-heavy extraction/regex chạy threadpool, không block event loop/polling.

## **7.5 Race-condition tests**

Bắt buộc có test barrier cho hai Create đồng thời để chứng minh chỉ một request acquire lease. Có test Retry trong khi session khác đang chạy: trả SYSTEM_BUSY, retry_count không tăng. Có test End Session và provider callback race: callback sau cleanup không được resurrect session.

# **8\. Document Processing và canonical text**

## **8.1 Extraction contract**

Extractor sinh một `canonical_text` + `extraction_version`. Parser-specific coordinates chỉ phục vụ dựng reading order; downstream không phụ thuộc PDF/DOCX coordinate. Mọi offset là **Unicode code point index sau NFC**.

Extraction/PyMuPDF/DOCX OOXML parsing chạy trong bounded threadpool để không block asyncio event loop; status endpoint phải vẫn đáp ứng NFR-PERF-02.

## **8.2 PDF**

* Validate MIME/extension, hard byte cap <=10MB; page_count <=30 trước full extraction.
* PyMuPDF đọc blocks/words; two-column page cluster x-position và đọc top-to-bottom trong từng cột.
* Header/footer lặp: normalized line xuất hiện >=60% trang ở vùng đầu/cuối trang; loại khỏi body. Page number đơn độc bị loại.
* Table: nếu detect rows/cells thì flatten row bằng ` | `, newline giữa rows.
* Text rỗng/image-only -> NO_EXTRACTABLE_TEXT.
* Sau extraction chạy quality gates §8.5, gồm legacy-font/mojibake heuristic cho TCVN3/VNI.

## **8.3 DOCX**

* python-docx đọc paragraph/table theo document order; lxml/OOXML xử lý numbering, tracked changes, textbox.
* Automatic numbering được materialize thành prefix text theo fixture hỗ trợ.
* Tracked changes: lấy accepted-state text; deleted bỏ, inserted giữ. Comment/footnote bỏ khỏi canonical body theo FR-08.
* Textbox đưa gần anchor paragraph; case không tái dựng ổn định phải ghi known limitation/fixture.
* Canonical char limit 100.000 sau normalization.

## **8.4 Canonicalization**

```text
canonicalize(chunks):
  1. normalize mỗi chunk Unicode NFC
  2. CRLF/CR -> LF
  3. NBSP -> normal space
  4. trim trailing spaces per line; không collapse structural newline
  5. cap blank lines liên tiếp ở 2
  6. join chunks theo document order bằng LF
  7. NFC lại và assert Unicode hợp lệ
```

Không lowercase, không bỏ dấu, không thay số/tiền/tỉnh/chức danh.

## **8.5 Quality gates**

| Gate | Default TDD 0.2 | Kết quả |
| :---- | :---- | :---- |
| Text hữu ích | >=100 ký tự non-whitespace | Dưới: NO_EXTRACTABLE_TEXT |
| Replacement U+FFFD | <= max(5, 0.2% chars) | Vượt: UNSUPPORTED_TEXT_ENCODING |
| Control chars ngoài LF/TAB | <=0.1% | Vượt: UNSUPPORTED_TEXT_ENCODING |
| Printable ratio | >=95% | Dưới: UNSUPPORTED_TEXT_ENCODING |
| Legacy-font suspicious glyph ratio | configurable, default >1% trên text >=200 chars | Kích hoạt secondary check |
| Vietnamese plausibility | secondary: từ phổ biến + dấu tiếng Việt + mojibake pattern | Fail -> UNSUPPORTED_TEXT_ENCODING |

Legacy-font detector không chỉ dựa U+FFFD. Nó dò các pattern thường gặp khi TCVN3/VNI bị extract sai như `®`, `¸`, `µ`, `¶`, `¬`, chuỗi dạng `Hîp`, `®ång`, kết hợp với tỷ lệ từ tiếng Việt hợp lệ thấp. Một ký tự đơn lẻ không đủ để reject; fixture font cũ trong D1/test phải fail như NFR-DATA-03 yêu cầu.

Các ngưỡng là cấu hình extraction version; chỉ tune trên D1, không T1/T2.

## **8.6 Offset contract cross-runtime**

Backend tính `start_char/end_char` bằng Python Unicode code point. API trả `offset_unit="unicode_code_point"`. Frontend JavaScript không được dùng trực tiếp index này với UTF-16 string khi có non-BMP; phải build mapping code point -> UTF-16 offset rồi mới highlight. Fixture có emoji/non-BMP để kiểm tra.

# **9\. Scope Precheck**

FR-06 dùng luật cục bộ, không LLM. Precheck match trên normalized copy và không sửa canonical text.

## **9.1 Rule set**

| Nhóm tín hiệu | Ví dụ | Điểm |
| :---- | :---- | :---- |
| Strong title | “hợp đồng lao động”, “hợp đồng thử việc” **trong `SCOPE_TITLE_SCAN_CHARS` ký tự đầu** | +3 |
| Party terms | “người lao động” và “người sử dụng lao động”/“bên sử dụng lao động” | +2 nếu có cả hai |
| Employment content | lương, thời giờ, công việc/chức danh, thời hạn | +1 mỗi nhóm, max +3 |
| Structure | >=2 heading Điều/Khoản hoặc mục quyền/nghĩa vụ | +1 |
| Strong negative | hóa đơn, mua bán, thuê nhà, dịch vụ thuần túy và không có employment party terms | -3 |

`Strong title` chỉ được tính khi phrase nằm trong 1.000 code point đầu (config) hoặc vùng title được extractor đánh dấu; mention “hợp đồng lao động” sâu trong thân tài liệu không tự động ACCEPT.

Decision default: ACCEPT nếu có strong title + ít nhất một employment signal; hoặc tổng score >=4 và có ít nhất một party term. REJECT nếu score <4 hoặc strong negative chiếm ưu thế. Hợp đồng thử việc và phụ lục nằm cùng file được chấp nhận. Fixture dương/âm khóa trước MS-2.

# **10\. PII Masking**

## **10.1 PII type và placeholder**

| Type | Short code | Tag ưu tiên | Ý nghĩa |
| :---- | :---- | :---- | :---- |
| PERSON\_NAME | N | \<NAME\> | Họ tên |
| DATE\_OF\_BIRTH | D | \<DOB\> | Ngày sinh |
| NATIONAL\_ID\_OR\_PASSPORT | I | \<ID\> | CCCD/hộ chiếu |
| RESIDENTIAL\_ADDRESS | R | \<ADDR\> | Địa chỉ cư trú |
| PHONE | P | \<PHONE\> | Số điện thoại |
| EMAIL | E | \<EMAIL\> | Email |
| BANK\_ACCOUNT | B | \<BANK\> | Số tài khoản |
| LEGAL\_ENTITY | O | \<ORG\> | Tên pháp nhân |

```python
def mask_value(text, pii_type):
    n = len(text)  # Unicode code points after NFC
    tag = TYPE_TAG[pii_type]  # ASCII tag
    if n >= len(tag):
        return tag + "_" * (n - len(tag))
    return TYPE_SHORT_CODE[pii_type] * n

assert len(mask_value(value, pii_type)) == len(value)
```

Ví dụ: `nguyenvana@gmail.com` -> `<EMAIL>____________` với đúng cùng số code point. Tên rất ngắn 2 ký tự -> `NN`. Dùng `_` thay ký tự block để giảm token; prompt chỉ giải thích type tag/code, không truyền original value.

## **10.2 Detection order**

* Regex/high-precision trước: email, phone, national ID/passport, bank account, date-of-birth với anchor, địa chỉ với anchor.  
* Heuristic entity sau: họ tên và tên pháp nhân dựa trên anchor như "Ông/Bà", "Người lao động", "Đại diện", "Công ty", "MST"; chỉ mask span value, không mask từ vai trò.  
* Preserve-list: lương/phụ cấp, thời hạn/ngày hiệu lực không phải DOB, giờ làm, chức danh, tỉnh/thành phố cấp tỉnh, từ NLĐ/NSDLĐ.  
* Overlap resolution: sort theo start, sau đó ưu tiên span dài hơn và type high-confidence; không cho overlap sau resolve.  
* Không sử dụng cloud NER/LLM. NER local chỉ được thêm nếu privacy metric trên D1 không đạt, theo SRS OI-12.

## **10.3 Boundary safety**

Masker trả pii\_spans\[{type,start,end}\]. Segmenter phải gọi boundary\_guard(pos): false nếu start \< pos \< end của bất kỳ pii\_span. Nếu regex heading tạo boundary trong placeholder thì boundary dời ra đầu/end placeholder gần nhất hoặc bỏ match.

# **11\. Clause Segmentation**

## **11.1 ID, span và partition invariant**

`clause_id` = `cl_0001`, `cl_0002`... theo `start_char` tăng dần; unique trong session. `original_text = canonical_text[start:end]`.

**Bắt buộc:** các clause là một partition các vùng được phân tích và **không chồng lấn span**. Với cấu trúc lồng nhau, hierarchy được lưu bằng metadata/PARENT_OF chứ không bằng span chứa span.

## **11.2 Structural heading patterns**

```regex
1. Article:        ^\s*Điều\s+(\d+[A-Za-z]?)\s*[.:-]?\s*(.*)$
2. Decimal:        ^\s*(\d+(?:\.\d+){1,3})\s*[.)-]?\s+(.+)$
3. Numbered item:  ^\s*(\d{1,3})[.)]\s+(.+)$
4. Lettered item:  ^\s*([a-zA-ZđĐ])[.)]\s+(.+)$
5. Dash bullet:    ^\s*[-–•]\s+(.+)$
```

Algorithm trước hết nhận các heading/list marker hợp lệ và gán `structure.level/number/parent`. Sau đó **mọi accepted boundary** kết thúc span clause trước đó, bất kể heading kế tiếp là parent hay child. Vì vậy:

* `Điều 5` có các khoản `5.1`, `5.2`: span của clause “Điều 5” chỉ gồm heading + lời dẫn trước `5.1`; không bao trùm text của child.
* `5.1` kết thúc trước `5.2`, không chồng nhau.
* Dash/letter bullet chỉ thành clause riêng khi rule list đủ tin cậy (>=2 siblings hoặc marker cấu trúc rõ); nếu không, nằm trong clause paragraph hiện tại.

Nếu một parent chỉ có heading rồi lập tức tới child, parent clause có thể chỉ gồm heading. Đây vẫn là clause hợp lệ cho hierarchy nhưng evaluation fixture phải nhất quán với annotation guideline.

## **11.3 Fallback paragraph**

* Không có heading đáng tin cậy -> split theo paragraph blocks.
* Paragraph <40 chars được gộp với neighbor nếu không phải heading/list.
* Không split giữa line khi không có marker.
* Clause >4.000 chars giữ nguyên baseline và ghi warning; không semantic split bằng LLM.
* Sau segmentation: <=150 clause; spans sorted; `end_i <= start_{i+1}`; không boundary trong placeholder.

## **11.4 Segmentation output schema**

```json
{
  "schema_version":"segmentation_v1",
  "segmentation_version":"rules_v1.1",
  "offset_unit":"unicode_code_point",
  "clauses":[
    {"clause_id":"cl_0001","original_text":"...","start_char":0,"end_char":95,
     "structure":{"level":1,"number":"5","parent_clause_id":null}}
  ]
}
```

`structure` là metadata local cho graph builder; public Clause chỉ cần field tối thiểu SRS. Raw original text/structure không gửi LLM nếu không cần.

# **12\. Clause Graph và Context Resolver**

## **12.1 Graph build**

| Edge | Cách dựng | Validation |
| :---- | :---- | :---- |
| NEXT | `clauses[i] -> clauses[i+1]` theo span | Node tồn tại; no self-loop. |
| PARENT_OF | từ hierarchy numbering | Parent level < child level; no cycle. |
| REFERS_TO | local regex/reference parser trên masked clause | Chỉ tạo khi resolve đúng duy nhất tới clause trong cùng contract. |

REFERS_TO phải loại trừ dẫn chiếu **văn bản pháp luật**. Không tạo contract edge nếu pattern có các context như `Bộ luật`, `Luật`, `Nghị định`, `Thông tư`, `văn bản pháp luật`, hoặc dạng `Điều 26 Bộ luật Lao động` / `Điều 26 của Bộ luật...`. Chỉ resolve “Điều/Khoản ...” khi số đó tồn tại trong contract structure index và reference context không chỉ ra external legal document. Ambiguous -> bỏ edge + diagnostic.

Graph object chỉ lưu node IDs + ClauseEdge; không text.

## **12.2 Context resolution**

```text
resolve_context(target):
  1. outgoing REFERS_TO targets
  2. incoming REFERS_TO sources
  3. direct parent và direct children PARENT_OF
  4. previous NEXT rồi next NEXT
  deduplicate, bỏ target
  lấy tối đa CLAUSE_GRAPH_MAX_RELATED và max context chars
```

Risk prompt dùng related clauses chỉ cho điều kiện/phụ thuộc/mâu thuẫn của **target clause**. Output vẫn target `clause_id`.

`CLAUSE_GRAPH_ENABLED=false` chỉ dùng dev/eval/test: graph build/context resolver bị bypass nhưng segmentation, original_text/span phải giống hệt. Demo require true theo FR-31.

## **12.3 ContextResolutionTrace - bằng chứng nghiệm thu**

Để chứng minh Clause Graph thực sự tham gia Validation & Reasoning mà không tự đổi SRS RiskResult, dev/eval tạo ephemeral diagnostic:

```json
{
  "target_clause_id":"cl_0007",
  "related":[
    {"clause_id":"cl_0002","relation":"REFERS_TO"},
    {"clause_id":"cl_0006","relation":"NEXT_PREV"}
  ],
  "included_in_risk_request":true,
  "context_chars":842
}
```

Trace không chứa contract text, không persist trong product runtime, và không xuất cho end user. Evaluation/demo evidence gồm: graph fixture đúng; trace cho biết ID context đã đưa vào LLM #2; graph on/off không đổi span; graph cleanup cùng session. Nếu nhóm muốn `related_clause_ids` trong RiskResult product, phải cập nhật SRS trước.

# **13\. Clause Classification LLM**

## **13.1 Request contract**

```json
{
  "schema_version":"clause_classification_request_v1",
  "taxonomy_version":"clause_taxonomy_v03",
  "items":[
    {"clause_id":"cl_0001","masked_text":"..."}
  ]
}
```

**Không gửi `role`** cho Clause Classification. FR-11 chỉ cần clause ID + masked clause và optional minimal structural context. Không gửi canonical/original/start/end.

## **13.2 Response contract**

```json
{
  "schema_version":"clause_output_v3",
  "items":[
    {"clause_id":"cl_0001","clause_labels":["COMPENSATION_BENEFITS"]}
  ],
  "model_id":"...",
  "prompt_version":"clause_prompt_v1",
  "taxonomy_version":"clause_taxonomy_v03"
}
```

* 1..3 labels, unique, từ source taxonomy.
* Không chấp nhận confidence/type_scores/tier/review_zone/quote/span.
* Missing/duplicate/unknown ID hoặc label invalid -> structured-output retry tối đa 1; sau đó AI_OUTPUT_INVALID.

## **13.3 Prompt policy**

System prompt: chỉ phân loại clause; không phân tích risk; không suy diễn PII đã che; chỉ chọn label taxonomy; output theo provider response schema.

## **13.4 LLMProvider abstraction và retry matrix**

```python
class LLMProvider(Protocol):
    async def generate_structured(self, *, model_id, messages, response_schema, timeout_s): ...
```

* `GeminiProductClient`: bắt buộc demo/eval, paid tier, explicit model ID, provider structured output/`response_schema`.
* `DevLocalClient` hoặc Gemini dev: optional chỉ `APP_ENV=dev` và de-identified data; không nằm product deployment.

| Lỗi | Auto-retry? | Lý do |
| :---- | :---- | :---- |
| Timeout/network reset | Có, tối đa 1 | Tạm thời. |
| HTTP 429 | Có, tối đa 1 với backoff/jitter | Tạm thời nhưng tính quota/cost. |
| HTTP 5xx | Có, tối đa 1 | Provider transient. |
| HTTP 400/401/403 | Không | Config/request/auth lỗi, retry vô ích. |
| Structured output/schema invalid | Có, tối đa 1 | Repair bằng cùng schema + validation feedback. |

Mỗi **actual provider request**, kể cả retry, tăng call counter/cost ledger.

# **14\. Legal Corpus, Baseline Retrieval và Data Graph**

## **14.1 Artifact layout**

```text
data/legal_corpus/
  manifest.yaml
  provisions.jsonl
  edges.jsonl
  edge_suggestions.jsonl   # optional, không load vào runtime graph
  label_map.yaml
```

`manifest.yaml` chứa corpus_version, graph_version, timezone và checksums.

## **14.2 LegalProvision JSONL**

```json
{
  "citation_id":"BLLD2019:art26",
  "document_id":"BLLD2019",
  "document_name":"Bộ luật Lao động 2019",
  "version":"2019",
  "article":"26",
  "clause":null,
  "point":null,
  "parent_path":["BLLD2019","art26"],
  "content":"...",
  "effective_from":"2021-01-01",
  "effective_to":null
}
```

`citation_id` deterministic. Nếu cùng provision có nhiều version theo thời gian, effectivity record chọn bản hiệu lực; overlap -> LEGAL_CORPUS_CONFLICT.

## **14.3 LegalEdge và origin**

Runtime LegalEdge chỉ dùng enum SRS `AUTO|MANUAL`:

* PARENT_OF sinh từ `parent_path` khi build -> origin=AUTO; không cần lưu trong `edges.jsonl`.
* `edges.jsonl` chỉ chứa REFERS_TO/GUIDES đã được người phụ trách dữ liệu xác minh -> origin=MANUAL.
* Gợi ý tự động chưa xác minh nằm ở `edge_suggestions.jsonl` và **không được load**. Khi reviewer duyệt, copy thành edge MANUAL.

```json
{"from_citation_id":"BLLD2019:art26","to_citation_id":"BLLD2019:art25",
 "edge_type":"REFERS_TO","origin":"MANUAL"}
```

## **14.4 Corpus validation**

* deterministic citation ID, valid effectivity, no overlap.
* edge endpoint tồn tại; PARENT_OF acyclic; enum hợp lệ.
* content UTF-8/NFC non-empty; metadata đủ export.

## **14.5 Baseline retrieval - cùng kích thước graph on/off**

`label_map.yaml` khai **trọng số trực tiếp**, không có khái niệm “nhóm label liên quan” ngầm:

```yaml
COMPENSATION_BENEFITS:   # khóa = một trong 12 nhãn clause taxonomy; giá trị chỉ là ví dụ minh họa
  BLLD2019:art26: 1.0
  BLLD2019:art25: 0.6
```

```text
baseline_score(c) = 0.70 * configured_label_weight(c)
                  + 0.30 * bm25_normalized(c)
```

Retriever luôn tính `baseline_pool = top RETRIEVAL_FINAL_K` sau effectivity + dedupe. `seeds = top RETRIEVAL_SEED_K` là subset dùng **chỉ để graph expansion**. Khi graph disabled/fallback, final candidates = baseline_pool (không phải chỉ 3 seed).

## **14.6 Data Graph expansion, hướng cạnh và ranking**

Convention edge:

* PARENT_OF: `from=parent`, `to=child`. Expansion được đi cả parent->child và child->parent; tối đa `GRAPH_MAX_CHILDREN_PER_SEED` child, chọn theo baseline/BM25 relevance.
* REFERS_TO: `from=source provision`, `to=referred provision`. Ưu tiên outgoing; incoming được phép như secondary fact-finding, tổng neighbor vẫn bị cap.
* GUIDES: `from=guiding provision`, `to=guided/base provision`. Cho phép traverse cả hai hướng để từ base tìm guidance và ngược lại.
* Tổng graph-only neighbor lấy từ mỗi seed <= `GRAPH_MAX_NEIGHBORS_PER_SEED`.

Scoring default (tune D1/D2):

```text
graph_score = 0.60 * seed.baseline_score + edge_bonus + direction_bonus
edge_bonus:
  REFERS_TO 0.30
  GUIDES     0.25
  PARENT_OF  0.15

direction_bonus:
  preferred direction 0.05
  reverse direction   0.00
```

Final merge:

1. Giữ top `seed_k` seed ở đầu theo baseline score (seed-first SDD).
2. Merge `baseline_pool[seed_k:]` và graph-only neighbors bằng score chuẩn hóa; dedupe citation ID.
3. Take `final_k`.

Do đó graph on/off đều có cùng tối đa `final_k=8`; M8 recall@5 là so sánh top 5 thực sự ở cả hai cấu hình. Risk LLM cũng nhận cùng candidate-count budget, tránh bias do graph-off ít candidate hơn.

Nếu graph runtime lỗi -> baseline_pool + `graph_fallback=true` trong RunLog.

## **14.7 LegalCandidate**

```json
{
  "citation_id":"BLLD2019:art26",
  "content":"...",
  "document_name":"Bộ luật Lao động 2019",
  "article":"26",
  "version":"2019",
  "effective_from":"2021-01-01",
  "effective_to":null,
  "origin":"SEED_LABEL|SEED_LEXICAL|BASELINE_BACKUP|GRAPH_PARENT_OF|GRAPH_REFERS_TO|GRAPH_GUIDES",
  "rank":1
}
```

# **15\. Risk Analysis, citation validation và assembly**

## **15.1 Risk LLM request - candidate catalog dedupe**

Một provider call dùng candidate catalog chung để không lặp full legal text cho mỗi item:

```json
{
  "schema_version":"risk_analysis_request_v2",
  "role":"EMPLOYEE",
  "risk_taxonomy":[
    {"label":"PROBATION_WAGE_BELOW_MINIMUM","basis_type":"LEGAL_VIOLATION","definition":"..."}
  ],
  "candidates":{
    "BLLD2019:art26":{"content":"...","metadata":{"document_name":"...","article":"26"}}
  },
  "items":[{
    "clause_id":"cl_0001",
    "masked_text":"...",
    "clause_labels":["COMPENSATION_BENEFITS"],
    "candidate_ids":["BLLD2019:art26"],
    "related_clauses":[{"clause_id":"cl_0002","relation":"REFERS_TO","masked_text":"..."}]
  }]
}
```

Candidate order của mỗi item nằm trong `candidate_ids`. Payload không original/span. `risk_taxonomy` cung cấp `basis_type` để model hiểu semantics; model response vẫn chỉ trả labels, backend derive basis type.

## **15.2 Risk LLM response**

```json
{
  "schema_version":"risk_output_v1",
  "items":[{
    "clause_id":"cl_0001",
    "risk_labels":["PROBATION_WAGE_BELOW_MINIMUM"],
    "severity":"HIGH",
    "explanation":"Mức lương thử việc thấp hơn mức tối thiểu trong căn cứ được cung cấp.",
    "evidence_status":"SUPPORTED",
    "citation_ids":["BLLD2019:art26"]
  }],
  "model_id":"...",
  "prompt_version":"risk_prompt_v1",
  "risk_taxonomy_version":"risk_taxonomy_v01",
  "severity_rubric_version":"severity_v01"
}
```

Gemini call bắt buộc dùng structured output/response schema tương ứng `risk_output_v1`.

## **15.3 Runtime validation và advice sanitizer**

* clause_id thuộc batch; risk labels thuộc taxonomy; role không do model trả.
* SUPPORTED => citation_ids non-empty, severity HIGH/MEDIUM/LOW.
* INSUFFICIENT_EVIDENCE => citation_ids empty, severity null.
* Citation IDs phải subset candidate IDs; ngoài candidate được log trước khi filter.
* Advice detector **không match từ `nên` đơn lẻ**. Match các pattern có ngữ nghĩa khuyến nghị như `bạn nên`, `NLĐ nên`, `NSDLĐ nên`, `nên sửa/bổ sung/thương lượng/yêu cầu`, `đề nghị sửa`, `khuyến nghị`.
* Explanation legal-reference lint: nếu text nhắc rõ “Điều/Khoản ...” hoặc tên văn bản mà không tương ứng với citation hợp lệ đã chọn, coi là unsupported reference.

Xử lý vi phạm advice/unsupported-reference:

1. Structured retry tối đa 1 lần với validation feedback.
2. Nếu vẫn vi phạm, backend xóa **câu vi phạm** bằng deterministic sentence sanitizer; giữ phần explanation trung tính còn lại.
3. Nếu sanitizer làm explanation rỗng hoặc mất toàn bộ rationale -> `AI_OUTPUT_INVALID` và FAILED. Không fail cả phiên chỉ vì một từ nối “nên” hợp lệ.

## **15.4 Citation Validator**

```text
selected_before_filter = risk.citation_ids
valid = []
for cid in selected_before_filter:
  if cid not in candidate_ids:
    log outside_candidate += 1
    continue
  provision = corpus.resolve(cid, analysis_date)
  if provision is effective:
    valid.append(cid)
if valid empty:
  evidence_status = INSUFFICIENT_EVIDENCE
  severity = null
citation_ids = unique(valid)
```

Runtime không tự chấm relevance semantic; M3b là evaluation property.

## **15.5 Result Assembler**

* Join RiskResult -> Clause bằng clause_id.
* Quote/start/end chỉ từ canonical Clause.
* Derive `risk_basis` cho từng risk label từ risk taxonomy; unknown mapping là internal error trước publish.
* Citation objects từ validated IDs.
* No-risk -> COMPLETED + exact no-risk message + disclaimer, không khẳng định an toàn.
* Final publish atomically; FAILED không expose partial.
* `ContextResolutionTrace` chỉ dev/eval; không đưa vào product response nếu SRS chưa cập nhật.

# **16\. Export report**

## **16.1 Report model**

| Phần | Nội dung |
| :---- | :---- |
| Header | Tên hệ thống, ngày phân tích, vai trò, filename hiển thị, version summary. |
| Disclaimer | Nội dung BRD Phụ lục A + câu không kiểm tra missing-clause risk. |
| **Data notice** | Thông báo xử lý dữ liệu cá nhân theo BRD Phụ lục A/FR-25. |
| Summary | Số clause, số clause có risk, HIGH/MEDIUM/LOW, số INSUFFICIENT_EVIDENCE. |
| Risk section | Original clause quote, risk label + basis type, severity/chưa đủ căn cứ, explanation, citations. |
| Citation appendix | Tên văn bản, điều/khoản/điểm, version/effectivity. |
| Technical footer | schema/version pins; không PII masking internals. |

Quote dùng original_text. DOCX/PDF cùng ReportModel để không lệch nội dung. Export phải chứa **cả disclaimer và data notice**.

## **16.2 Lifecycle**

Exporter tạo bytes in-memory nếu có thể; temp file chỉ khi renderer cần. Sau stream/error xóa ngay, không cache server-side.

# **17\. Logging, quota, rate limit, retention và security**

## **17.1 RunLog schema**

```text
run_log(
  id INTEGER PK,
  session_id TEXT,
  stage TEXT,
  started_at TEXT,
  duration_ms INTEGER,
  calls INTEGER,
  input_tokens INTEGER,
  output_tokens INTEGER,
  estimated_cost REAL,
  error_code TEXT,
  graph_enabled INTEGER,
  graph_added_candidates INTEGER,
  created_at TEXT
)
```

Không raw filename nếu có PII; persistent log chỉ extension/size. Không prompt/canonical/masked/quote/PII.

## **17.2 Daily quota và admission reservation**

Mỗi actual provider request, kể cả retry, tăng daily counter atomically trước call. Phiên đang chạy không bị dừng khi counter vượt do retry; upload mới sau đó bị chặn, đúng BR-16.

TDD 0.2 bỏ “reserve 4 calls”. Trước demo, D1 phải đo `planned_calls = ceil(n_clause/CLAUSE_BATCH_SIZE) + ceil(n_clause/RISK_BATCH_SIZE)` cho từng contract. `SESSION_CALL_RESERVE` được cấu hình bằng p95 planned calls (hoặc conservative value nhóm chốt). Admission cho session mới chỉ pass khi:

```text
remaining_daily_calls >= SESSION_CALL_RESERVE
```

Vì actual retries có thể vượt reserve, current session vẫn hoàn tất; counter có thể vượt nhẹ quota nhưng hệ thống không nhận session mới. Báo cáo cost phải ghi cả planned vs actual calls.

`DAILY_LLM_CALL_QUOTA` **không có default 120 trong demo**. Nhóm phải chốt từ số call/token/cost D1 + giá model cụ thể + phần ngân sách vận hành $5. Ví dụ kỹ thuật: với 40-60 clause và batch 20/6, planned calls xấp xỉ 9-13 trước retry; đây là lý do không nên dùng một quota tùy ý mà không đo.

## **17.3 Evaluation budget isolation**

`APP_ENV=eval` không dùng runtime quota/rate counter SQLite của product. Evaluation harness có `eval_cost_ledger.json/csv` riêng và vẫn log actual calls/tokens/cost để kiểm soát phần ngân sách đánh giá $15.

## **17.4 IP rate limit**

Sliding window: tối đa 5 Create requests/10 phút/IP mặc định. Persistent key là HMAC-SHA256(server_salt, IP) truncated; raw IP chỉ request context.

## **17.5 Retention và cleanup**

* last_activity cập nhật Create/Result/Retry/Export/End; Status polling không tính.
* Cleanup mỗi 60s; inactivity >=60 phút -> cancel, delete temp/content, tombstone EXPIRED.
* Tombstone chỉ session_id/status/expired_at, giữ 24h.
* Restart không restore session. Startup dọn temp stale >2h.

## **17.6 Performance/cost measurement gate**

NFR-PERF-01 chỉ áp dụng PDF <=15 trang hoặc DOCX <=50.000 chars; **không cam kết 120s cho input max 150 clause**. Trước MS-2 chạy D1 benchmark và ghi p50/p90 cho: local preprocessing, LLM #1, retrieval/graphs, LLM #2, assembly. Batch size/parallelism chỉ được khóa sau số đo này.

Timeout 30s + one retry có thể làm một call gần 60s; vì vậy benchmark phải có cả case provider latency injection. Nếu p90 >120s, ưu tiên giảm payload token, tăng batch hợp lý hoặc giảm context trước khi thay invariant.

## **17.7 Security checklist**

| Kiểm soát | Thiết kế/TDD test |
| :---- | :---- |
| HTTPS | TLS ở deployment. |
| Secrets | ENV/secret store; key qua header; no log. |
| Session isolation | exact session_id lookup + negative tests. |
| Upload safety | hard byte cap, sniff type, random temp dir, sanitize display filename. |
| LLM boundary | outbound capture không raw PII/canonical. |
| Logs | automated PII scan. |
| No durable contract data | DB/temp/restart audit. |
| Single worker | deployment smoke fail nếu cấu hình >1 worker trong demo profile. |

# **18\. Evaluation Harness và gold format**

## **18.1 CLI**

```bash
python -m ai_pipeline.evaluation.runner --dataset T1 --config configs/eval.yaml --output evaluation/runs/run_001/
python -m ai_pipeline.evaluation.runner --dataset T2 --metric M8 --graph-enabled true
python -m ai_pipeline.evaluation.runner --dataset T2 --metric M8 --graph-enabled false
```

Harness dùng shared modules trực tiếp, không HTTP, không product quota/rate-limit. Input de-identified. Chi phí ghi eval ledger riêng.

## **18.2 Dataset manifest**

```json
{
  "dataset":"T2",
  "dataset_version":"t2_v1",
  "documents":[{
    "doc_id":"t2_001",
    "file":"contracts/t2_001.docx",
    "role_variants":["EMPLOYEE","EMPLOYER"],
    "gold_segmentation":"gold/t2_001.seg.json",
    "gold_clause_labels":"gold/t2_001.clause.json",
    "gold_risks":"gold/t2_001.risk.json",
    "injected_errors":"gold/t2_001.injected.json",
    "privacy_gold":"gold/t2_001.privacy.json"
  }]
}
```

## **18.3 Gold formats**

| Artifact | Tối thiểu |
| :---- | :---- |
| seg.json | start_char,end_char,gold clause ref, offset_unit |
| clause.json | gold labels, annotator/source, taxonomy_version |
| risk.json | clause ref, role, risk_label, basis_type, gold citation_id, source |
| injected.json | injection_id, clause ref, role, risk_label, gold citation_id, insertion span |
| privacy.json | PII gold spans/types + preserve-field spans |
| judge.json | output id, human labels x2, adjudicated label, judge label |
| annotation.json | item id, annotator A/B labels để tính Cohen kappa của gold annotation subset |
| context_trace.json | target clause + related clause IDs/relation + included_in_request (dev/eval only) |

Khi nạp gold clause từ dataset của data repo (bản v06 trở đi): mỗi dòng một nhãn; `clause_text` không gồm heading/phần hành chính; mỗi dòng có `offset_quality` ∈ {`EXACT`, `CONTEXT`}. Dòng `CONTEXT` giữ `span=null` ở phía consumer, **không** được chấm như gold span chính xác (M1, M4); source-reference span riêng chỉ dùng để highlight/đối chiếu. Dataset này là gold **nhãn clause**; gold segmentation cho M1 vẫn do người sửa tay ranh giới (BRD 8.2 quy tắc 3).

## **18.4 Metric implementation mapping**

| Chỉ số | Module | Ghi chú |
| :---- | :---- | :---- |
| M1 | metrics/segmentation.py | IoU char >=0.80, greedy decreasing IoU. |
| M2 | metrics/risk_classification.py | Macro-F1 (clause,role,risk label). |
| M3a | metrics/citation_validity.py | candidate + corpus + effectivity. |
| M3b | metrics/citation_relevance.py | human/judge import. |
| M4 | metrics/quote_span.py | exact substring + code-point offset. |
| M5 | metrics/injected_recall.py | clause, role, label. |
| M6 | metrics/judge_calibration.py | Judge-human agreement + kappa. |
| M7 | metrics/clause_classification.py | Macro-F1 per clause label. |
| M8 | metrics/retrieval.py | Recall@5 graph on/off, **cùng final_k**. |
| BRD 7.3 privacy | metrics/privacy.py | PII recall theo nhóm + preserve rate. |
| Annotation agreement | metrics/annotation_agreement.py | Cohen kappa trên >=20% item gán đôi theo BRD 8.2. |
| BL-1 | metrics/baseline_comparison.py | Citation error rate system vs baseline nếu chưa cut. |

## **18.5 M8 protocol - predicted labels là primary**

Primary M8 chạy **pipeline thực tế**: segmentation + **predicted clause labels** -> retrieval. Đây là số báo chính vì FR-12 runtime dùng predicted labels. Graph on/off dùng cùng input, model output cache (nếu hợp lệ), same `final_k`, same corpus/config ngoài graph flag.

Có thể chạy thêm `M8-oracle-labels` với gold clause labels để chẩn đoán retriever độc lập khỏi M7, nhưng phải ghi rõ đây là diagnostic, không thay M8 chính.

## **18.6 Clause Graph evidence**

FR-31 không có metric chất lượng riêng trong BRD. Harness xuất ContextResolutionTrace và test fixture xác nhận REFERS_TO/PARENT_OF context được đưa vào Risk request. Đây là bằng chứng kỹ thuật; không tuyên bố “graph cải thiện accuracy” nếu chưa có metric/upstream requirement.

Evaluation output luôn ghi version pins, config snapshot và commit. Locked eval cấm override prompt/config ngoài allowlist sau MS-3.

# **19\. Test strategy**

## **19.1 Test pyramid**

| Mức | Ví dụ bắt buộc |
| :---- | :---- |
| Unit | canonicalization, code-point offsets, PII placeholder length, legacy-font detector, segmentation partition, graph build, citation ID/effectivity, quota arithmetic. |
| Contract | Pydantic/JSON Schema, Gemini response_schema mock, API error body, risk_basis derivation. |
| Integration | PDF/DOCX -> canonical -> mask -> segment; corpus build; graph fair on/off; retry/lease/cleanup. |
| E2E mock LLM | 6 operations, state transitions, no partial, frontend polling contract, export DOCX. |
| Provider smoke | Gemini paid tier de-identified fixture, retry matrix, token/cost log. |
| Evaluation | M1-M8 + privacy + annotation kappa + BL-1(if enabled), context trace. |

## **19.2 Critical invariant tests**

| ID | Invariant | Test |
| :---- | :---- | :---- |
| INV-01 | len(masked)==len(canonical) code points | Privacy fixtures. |
| INV-02 | canonical[start:end]==original | Segmentation fixtures. |
| INV-03 | clause spans non-overlap + boundary not in PII | Nested/list adversarial fixtures. |
| INV-04 | outbound only masked contract text | Transport capture. |
| INV-05 | LLM cannot override span/quote | Malicious extra fields. |
| INV-06 | citation subset candidate + effective corpus | Fake citation. |
| INV-07 | INSUFFICIENT => severity null, citations empty | Risk schema. |
| INV-08 | Clause Graph contains no text | Object/serialization inspection. |
| INV-09 | restart removes session content | Process restart. |
| INV-10 | FAILED never returns final | Error injection. |
| INV-11 | graph off/on same final_k for M8 | Retrieval fixture. |
| INV-12 | JS highlight conversion correct for non-BMP | Browser/unit fixture. |

## **19.3 API/state tests**

* ROLE_REQUIRED/RATE/QUOTA/SYSTEM_BUSY pre-admission không tạo session.
* Hai Create đồng thời: chỉ một acquire lease.
* Invalid file sau 201 -> session REJECTED + error_code qua Status.
* REJECTED retry -> INVALID_SESSION_STATE; FAILED retry #1/#2; #3 RETRY_LIMIT_EXCEEDED.
* Retry khi another session active -> SYSTEM_BUSY, counter không tăng.
* Local FAILED retry -> VALIDATING; processing FAILED retry -> PROCESSING.
* Polling status không kéo TTL; Result/Export kéo TTL.
* End Session trả 200 + EXPIRED, cancel tasks, idempotent.
* EXPIRED tombstone 24h rồi SESSION_NOT_FOUND.

## **19.4 Fixture format**

Repository fixture tối thiểu:

```text
tests/fixtures/
  extraction/
    pdf_two_column/{input.pdf, expected.json}
    pdf_legacy_tcvn3/{input.pdf, expected_reject.json}
    docx_numbering/{input.docx, expected.json}
  privacy/
    case_001.json
  segmentation/
    nested_article_subclauses.json
    paragraph_fallback.json
  clause_graph/
    refers_contract.json
    excludes_legal_reference.json
  legal_corpus/
    valid/
    invalid_overlap/
    invalid_edge/
  api/
    state_cases.json
```

`expected.json` extraction chứa `canonical_text`, `extraction_version`, `offset_unit`; segmentation fixture chứa input canonical/masked + expected ordered spans/hierarchy; graph fixture chứa clauses + expected edges; privacy fixture chứa canonical + gold PII/preserve spans; API fixture chứa starting state, operation, expected HTTP/code/state. Fixture content có hợp đồng thật phải de-identify thủ công theo BRD 7.6.

# **20\. Traceability và kế hoạch migration codebase**

## **20.1 SRS \-\> TDD module**

| SRS | Module | TDD |
| :---- | :---- | :---- |
| FR-01..06,26,27 | api/session/orchestrator/scope\_precheck/ops | API §5, Orchestrator §7, Scope §9, Ops §17 |
| FR-07,08 | document/\* | §8 |
| FR-09 | clause/segmenter.py | §11 |
| FR-10 | privacy/\* | §10 |
| FR-11,28,29 | ai/clause\_adapter.py, ai/client.py | §13, §4 |
| FR-12,24,30 | legal/corpus\*, baseline\_retriever.py, data\_graph.py | §14 |
| FR-13..18 | ai/risk\_adapter.py, legal/citation\_validator.py | §15 |
| FR-19,20 | result/assembler.py + frontend contract | §15, §5.9 |
| FR-21 | session/orchestrator.py \+ ai/client.py | §7 |
| FR-22 | result/exporter.py | §16 |
| FR-23 | session/cleanup.py | §17.4 |
| FR-25 | frontend/export constants | §5.9/§16 |
| FR-31 | clause/graph\_builder.py \+ context\_resolver.py | §12 |
| EV-01..08 | evaluation/\* | §18 |

## **20.2 Migration từ snapshot codebase**

| Milestone kỹ thuật | SRS Appendix C | Kết quả |
| :---- | :---- | :---- |
| M0 \- Schema first | C-04,C-03,C-17 | Tạo enums/source-of-truth taxonomy, schema clause\_output\_v3/risk\_output\_v1, pytest skeleton và mocks mới. |
| M1 \- Session/API | C-05,C-06,C-16 | InMemorySessionStore, state machine, 6 operation, global lock, metadata-only ops DB. |
| M2 \- Local preprocessing | C-08,C-10,C-09,C-01,C-02 | Extractor PDF/DOCX, scope, masking, segmentation; ưu tiên invariant trước AI. |
| M3 \- AI classification | C-07,C-11 | Gemini client chuẩn, classification batch. |
| M4 \- Legal retrieval | C-12,C-13 | Corpus validator, baseline retriever, Data Graph. |
| M5 \- Risk \+ Clause Graph | C-14,C-15 | Clause Graph context \+ risk call \+ citation validation/assembly. |
| M6 \- Output/Eval | C-21,C-18,C-19,C-20 | Export DOCX, evaluation metrics, docs/dependency cleanup. |

Nguyên tắc migration: không tiếp tục phát triển trên schema cũ có contract\_id/type\_scores/review\_zone. Mock schema mới phải có trước để backend/frontend/AI có thể làm song song.

# **21\. Open items / giới hạn đã biết**

| ID | Mục | Xử lý | Ảnh hưởng |
| :---- | :---- | :---- | :---- |
| O-01 | Risk taxonomy v01 chưa có trong nguồn | TDD dùng placeholder; phải đóng băng MS-1. | Block prompt/eval final. |
| O-02 | DOCX numbering/textbox cases phụ thuộc D1/T1 | Chỉ support fixture chốt; ghi known limitation. | FR-08/OI-11. |
| O-03 | PII local rules có thể chưa đạt recall tên/địa chỉ/pháp nhân | Đo D1 sớm; thêm local NER nếu cần. | OI-12. |
| O-04 | Daily quota + session call reserve chưa có số cost thực | Đo D1, chốt trước demo/MS-2. TDD 0.2 cố ý không giữ số 120 tùy ý. | FR-27/NFR-COST. |
| O-05 | Batch/parallelism/graph weight/neighbor cap cần benchmark | Tune D1/D2, version config. | PERF/M8. |
| O-06 | REFERS_TO/GUIDES legal edges cần người dữ liệu xác minh | Trễ thì cut item 5, giữ structural edges. | BRD 9.5. |
| O-07 | PDF export có thể bị cắt | DOCX vẫn đầy đủ. | Cut item 4. |
| O-08 | Stage resume có thể bị cắt | Retry từ đầu, max 2. | Cut item 2. |
| O-09 | API-state codes của §5.8 chưa backport SRS 6.2 | Không đổi state semantics; đề xuất cập nhật SRS để trace. | Documentation consistency. |
| O-10 | Nếu muốn `related_clause_ids` trong RiskResult product | Phải sửa SRS 4.1/4.3 trước; hiện chỉ ContextResolutionTrace dev/eval. | Clause Graph observability. |
| O-11 | SDD sơ đồ state chưa vẽ VALIDATING -> FAILED; Cleanup Scheduler/component và startup numbering có lỗi trình bày | Không sửa SDD trong TDD; cần cập nhật SDD ở revision kế tiếp. | Doc consistency. |
| O-12 | Không có luật sư xác minh legal correctness toàn diện | Disclaimer, closed corpus, evaluation limitations. | BRD 8/10. |

Các DEC-16..21 trong SRS vẫn có mục “đề xuất/chờ nhóm duyệt” ở một số dòng. Nếu nhóm đổi các quyết định đó, SDD/TDD phải được version lại; TDD 0.2 không tự coi chúng đã được phê duyệt.

# **Phụ lục A. JSON Schema mẫu**

## **A.1 clause_output_v3**

```json
{
  "$id":"clause_output_v3",
  "type":"object",
  "additionalProperties":false,
  "required":["schema_version","items","model_id","prompt_version","taxonomy_version"],
  "properties":{
    "schema_version":{"const":"clause_output_v3"},
    "items":{"type":"array","items":{
      "type":"object","additionalProperties":false,
      "required":["clause_id","clause_labels"],
      "properties":{
        "clause_id":{"type":"string","pattern":"^cl_[0-9]{4}$"},
        "clause_labels":{"type":"array","minItems":1,"maxItems":3,"uniqueItems":true,
          "items":{"type":"string","enum":"<generated from taxonomy source>"}}
      }
    }},
    "model_id":{"type":"string"},
    "prompt_version":{"type":"string"},
    "taxonomy_version":{"type":"string"}
  }
}
```

Enum label phải sinh từ source-of-truth taxonomy hoặc có test đối chiếu theo DEC-20.

## **A.2 risk_output_v1**

```json
{
  "$id":"risk_output_v1",
  "type":"object",
  "additionalProperties":false,
  "required":["schema_version","items","model_id","prompt_version",
              "risk_taxonomy_version","severity_rubric_version"],
  "properties":{
    "schema_version":{"const":"risk_output_v1"},
    "items":{"type":"array","items":{
      "type":"object","additionalProperties":false,
      "required":["clause_id","risk_labels","severity","explanation",
                  "evidence_status","citation_ids"],
      "properties":{
        "clause_id":{"type":"string"},
        "risk_labels":{"type":"array","uniqueItems":true,"items":{"type":"string"}},
        "severity":{"type":["string","null"],"enum":["HIGH","MEDIUM","LOW",null]},
        "explanation":{"type":"string","minLength":1},
        "evidence_status":{"enum":["SUPPORTED","INSUFFICIENT_EVIDENCE"]},
        "citation_ids":{"type":"array","uniqueItems":true,"items":{"type":"string"}}
      }
    }}
  }
}
```

`risk_basis` **không nằm trong AI schema**; backend derive từ risk taxonomy. Pydantic model thực hiện cross-field validation SUPPORTED/INSUFFICIENT_EVIDENCE. Cùng JSON Schema được truyền làm provider response schema/structured output.

# **Phụ lục B. .env.example**

```dotenv
APP_ENV=dev
GEMINI_API_KEY=
GEMINI_MODEL_ID=
DEV_LLM_PROVIDER=gemini
LLM_TIMEOUT_SECONDS=30
LLM_AUTO_RETRY=1
CLAUSE_BATCH_SIZE=20
RISK_BATCH_SIZE=6
LLM_PARALLELISM=2
MAX_UPLOAD_MB=10
MAX_PDF_PAGES=30
MAX_DOCX_CHARS=100000
MAX_CLAUSES=150
SESSION_TTL_MINUTES=60
EXPIRED_TOMBSTONE_HOURS=24
# Bắt buộc cấu hình trước demo sau cost model D1:
DAILY_LLM_CALL_QUOTA=
SESSION_CALL_RESERVE=
RATE_LIMIT_UPLOADS=5
RATE_LIMIT_WINDOW_SECONDS=600
DATA_GRAPH_ENABLED=true
CLAUSE_GRAPH_ENABLED=true
RETRIEVAL_SEED_K=3
RETRIEVAL_FINAL_K=8
GRAPH_MAX_NEIGHBORS_PER_SEED=4
GRAPH_MAX_CHILDREN_PER_SEED=2
CLAUSE_GRAPH_MAX_RELATED=3
CLAUSE_GRAPH_MAX_CONTEXT_CHARS=6000
SCOPE_TITLE_SCAN_CHARS=1000
TEMPERATURE=0.0
LEGAL_CORPUS_DIR=./data/legal_corpus
OPS_DB_PATH=./runtime/ops_metadata.sqlite3
```

Demo profile phải chạy 1 worker. `APP_ENV=eval` bypass runtime quota/rate nhưng vẫn cần Gemini model/key và eval cost ledger.

# **Phụ lục C. Prompt contract**

## **C.1 Clause prompt - bắt buộc**

* Nhận `clause_id + masked_text`; **không role**, canonical original/span.
* Chọn 1-3 labels từ taxonomy version.
* Không risk/advice/confidence.
* Provider structured output theo `clause_output_v3`, không Markdown.

## **C.2 Risk prompt - bắt buộc**

* Nhận role, target masked clause, clause labels, candidate IDs/catalog và optional related clauses.
* Risk taxonomy đi kèm label + `basis_type` + definition; model chọn label, backend derive basis type.
* Chỉ clause hiện có; không missing-clause risk.
* Citation chỉ candidate IDs. Không nhớ/viện dẫn luật ngoài candidate.
* Thiếu căn cứ -> INSUFFICIENT_EVIDENCE, severity null, citations empty.
* related_clauses chỉ context cho điều kiện/phụ thuộc/mâu thuẫn; output vẫn target clause_id.
* Explanation tiếng Việt, trung tính; không lời khuyên/hành động; không nhắc điều luật ngoài selected valid citations.
* Provider structured output theo `risk_output_v1`, không quote/span/Markdown.

# **Phụ lục D. Checklist trước khi khóa demo**

| Hạng mục | Điều kiện |
| :---- | :---- |
| Schema | clause_output_v3/risk_output_v1/final_result_v1 pass; risk_basis derive đúng. |
| Privacy | BRD 7.3 đạt; outbound no raw PII; placeholder same length. |
| Span | M4=100%; non-overlap partition; Unicode code-point offset; browser non-BMP test. |
| Corpus | Build legal corpus/Data Graph pass; suggestions chưa verify không load. |
| Graph | M8 graph on/off same final_k; Clause Graph build/cleanup/context trace đúng. |
| LLM | Explicit Gemini model, response schema, timeout 30s, retry matrix, token/cost log. |
| State | Async REJECTED, lease race, local/process retry target, retry limit pass. |
| Performance | D1 p50/p90 đo và NFR-PERF-01/NFR-PERF-02 có evidence. |
| Cost | DAILY_LLM_CALL_QUOTA + SESSION_CALL_RESERVE chốt từ D1/cost model; eval ledger riêng. |
| Deployment | 1 worker, no autoscale/serverless; CPU-heavy local work dùng threadpool. |
| No persistence | Restart xóa session content; ops DB/log no contract content. |
| Export | DOCX đủ quote, risk/basis, disclaimer, **data notice**, citation; PDF nếu enabled. |
| Frontend | Polling <=2s status visibility; no-risk/insufficient/error catalog/highlight rules pass. |
| Eval | M1-M8 + privacy + annotation kappa + BL-1(if enabled); M8 primary dùng predicted labels. |
| Locked test | T1/T2 run ghi commit/version pins; không tuning sau test result. |

# **Phụ lục E. Catalog thông báo UI tối thiểu**

| Code/state | Thông báo tiếng Việt đề xuất |
| :---- | :---- |
| SYSTEM_BUSY | Hệ thống đang xử lý một hợp đồng khác. Vui lòng thử lại sau. |
| QUOTA_EXCEEDED | Hệ thống đã đạt giới hạn phân tích hiện tại. Vui lòng thử lại sau. |
| RATE_LIMITED | Bạn gửi yêu cầu quá nhanh. Vui lòng chờ rồi thử lại. |
| UNSUPPORTED_FILE_TYPE | Chỉ hỗ trợ tệp PDF hoặc DOCX có sẵn văn bản. |
| FILE_TOO_LARGE | Tệp vượt giới hạn dung lượng cho phép. |
| PDF_PAGE_LIMIT_EXCEEDED | PDF vượt giới hạn số trang cho phép. |
| DOCX_TEXT_LIMIT_EXCEEDED | DOCX có nội dung vượt giới hạn ký tự cho phép. |
| NO_EXTRACTABLE_TEXT | Không trích xuất được văn bản. Hệ thống chưa hỗ trợ tệp scan/ảnh. |
| UNSUPPORTED_TEXT_ENCODING | Văn bản trích xuất không đọc được hoặc dùng mã/font chưa hỗ trợ. |
| NOT_LABOR_CONTRACT | Tài liệu không được nhận diện là hợp đồng lao động trong phạm vi hệ thống. |
| TOO_MANY_CLAUSES | Hợp đồng có quá nhiều điều khoản để xử lý trong bản demo. |
| AI_TIMEOUT / AI_PROVIDER_ERROR | Dịch vụ phân tích tạm thời gặp lỗi. Bạn có thể thử lại nếu phiên cho phép. |
| AI_OUTPUT_INVALID | Kết quả AI không đúng định dạng kỹ thuật. Bạn có thể thử lại nếu phiên cho phép. |
| REJECTED | Tệp đã bị từ chối; muốn thử tệp khác cần mở phiên mới. |
| INSUFFICIENT_EVIDENCE | Chưa đủ căn cứ pháp lý trong kho luật. |
| COMPLETED no-risk | Không phát hiện rủi ro trong phạm vi phân tích. Kết quả không đồng nghĩa hợp đồng an toàn. |
| EXPIRED | Phiên đã kết thúc và dữ liệu phiên đã được xóa. |

# **Nguồn tài liệu dùng cho TDD**

1\. BRD: AI Labor Contract Risk Analyzer, phiên bản 0.5, 12/10/2026.

2\. SRS: AI Labor Contract Risk Analyzer, phiên bản 1.3, 12/10/2026.

3\. SDD: AI Labor Contract Risk Analyzer, phiên bản 0.1 Draft, 12/10/2026.

Mọi ID BR-/FR-/NFR-/DEC-/EV-/OI- trong tài liệu này giữ nguyên ý nghĩa từ các tài liệu nguồn. Các quyết định TDD-xx là chi tiết triển khai mới được khóa ở lớp Technical Design và không được phép sửa yêu cầu nguồn.