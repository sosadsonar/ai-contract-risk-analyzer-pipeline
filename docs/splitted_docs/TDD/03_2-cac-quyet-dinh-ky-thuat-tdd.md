<!-- nguồn: TDD_AI_Labor_Contract_Risk_Analyzer_v0.2.md | mục: 2. Các quyết định kỹ thuật TDD | 4893 ký tự | trước: 02_1-muc-dich-pham-vi-va-invariant-ky-thuat.md | sau: 04_3-stack-trien-khai-va-cau-truc-repository.md -->

# 2. Các quyết định kỹ thuật TDD

| ID | Quyết định | Lý do / nguồn |
|---|---|---|
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
| TDD-23 | Product `RiskResult` giữ `risk_labels[]` theo SRS; LLM trả `basis_type` (một giá trị cho mỗi clause); backend kiểm (label, basis_type, vai trò) theo risk taxonomy rồi dựng `risk_basis[] = [{label,basis_type}]` cho final API/UI/export; severity do backend tra bảng. | Giữ tương thích SRS 4.1/FR-13 và tránh mất loại rủi ro. |
| TDD-24 | Clause Graph không thêm field product mới chưa có trong SRS. Dev/eval sinh `ContextResolutionTrace` để chứng minh related clauses nào đã được đưa vào Risk LLM. | Nghiệm thu FR-31 mà không tự đổi SRS. |
| TDD-25 | `LLMProvider` abstraction cho phép Gemini paid ở demo/eval và optional local/dev adapter chỉ với dữ liệu de-identified; product path không tự host model. | NFR-SEC-06, SRS C-07. |

| Các giá trị batch/rate/graph weight/neighbor cap là default kỹ thuật và có thể tune **chỉ trên D1/D2 trước khi khóa demo**. Daily call quota phải có số đo cost model trước demo; không được tune trên T1/T2. |
|---|
