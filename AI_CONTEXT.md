# AI_CONTEXT.md — Đọc file này đầu tiên

> Dành cho AI (và thành viên mới). File ngắn, chỉ chứa thứ **luôn đúng** và **chỉ dẫn tìm tiếp**.
> Chi tiết nằm ở `docs/splitted_docs/` (tạo bằng `python scripts/split_doc.py` từ project root).
> File liên quan: `ARCHITECTURE.md` (kiến trúc, tech stack), `SKELETON.md` (hàm, API, tương tác), `PROGRESS.md` (kế hoạch 8 tuần).

## 1. Dự án trong 6 dòng

- **AI Labor Contract Risk Analyzer**: web app phân tích rủi ro **hợp đồng lao động tiếng Việt** (PDF/DOCX có text) theo **vai trò** `EMPLOYEE` (NLĐ) hoặc `EMPLOYER` (NSDLĐ).
- Đầu ra: danh sách rủi ro gắn với từng điều khoản (clause): `risk_labels`, `risk_basis`, `severity`, `explanation`, `citation_ids`, kèm highlight trên **canonical text**.
- Căn cứ pháp lý chỉ lấy từ **kho luật đóng** (closed corpus); không đủ căn cứ → `INSUFFICIENT_EVIDENCE`, không bịa citation.
- Bắt buộc có **Data Graph** (đồ thị kho luật, phục vụ retrieval) và **Clause Graph** (đồ thị điều khoản trong 1 hợp đồng, phục vụ reasoning) — giảng viên yêu cầu (BR-17, BR-18).
- Nhóm 5 người, **8 tuần xây dựng** (12/10 → demo 06/12/2026) + 2 tuần đánh giá. Ngân sách $20 ($5 vận hành, $15 đánh giá). Không có luật sư.
- Chỉ **2 lần gọi LLM** bắt buộc (Gemini Flash trả phí): (1) Clause Classification, (2) Risk + Explanation + chọn citation (severity do backend tra bảng taxonomy). Mọi thứ còn lại chạy local.

## 2. Thứ tự ưu tiên nguồn (khi tài liệu mâu thuẫn)

`BRD 0.5` (nghiệp vụ, chỉ số) **>** `SRS 1.4` (FR/NFR, entity, state, mã lỗi) **>** `SDD 0.1` (kiến trúc) **>** `TDD 0.2` (chi tiết kỹ thuật).
TDD sai so với BRD/SRS thì **TDD phải sửa**. Không tự ý đổi schema sản phẩm (vd thêm `related_clause_ids` vào RiskResult) khi SRS chưa sửa.

## 3. Invariant — KHÔNG BAO GIỜ phá

1. `canonical_text` là nguồn duy nhất cho quote, span, highlight, export quote.
2. PII masking chạy trên **toàn** canonical_text **trước** segmentation; `len(masked_text) == len(canonical_text)` (tính theo Unicode code point, sau NFC). Không có bảng ánh xạ placeholder → giá trị gốc.
3. Mỗi clause: `canonical_text[start_char:end_char] == original_text`; clause là **partition không chồng lấn**; không có ranh giới nằm trong placeholder; ≤ 150 clause.
4. Mọi offset = **Unicode code point** sau NFC. Frontend JS phải đổi code point → UTF-16 index trước khi slice/highlight.
5. Chỉ **masked text** được gửi ra LLM. LLM **không** nhận role ở bước classification, **không** tạo/sửa span/quote. Mọi output AI join bằng `clause_id`.
6. Citation ∈ candidate list ∈ closed corpus ∈ hiệu lực tại `analysis_date`. `INSUFFICIENT_EVIDENCE` ⇒ `citation_ids=[]` và `severity=null`.
7. Clause Graph chỉ chứa `clause_id` + `edge_type` (không có text), không đổi segmentation/span. `REFERS_TO` loại trừ dẫn chiếu văn bản pháp luật ("Điều 26 Bộ luật Lao động…").
8. LLM trả `risk_labels` và `basis_type` (một giá trị cho mỗi clause); backend kiểm (label, basis_type, role) theo risk taxonomy, dựng `risk_basis` và tra `severity` từ bảng. LLM không trả `severity`.
9. Không lưu nội dung hợp đồng ở nơi bền vững. Session ở RAM, TTL 60 phút không hoạt động; restart = mất session. SQLite chỉ chứa metadata (RunLog, quota, rate, tombstone).
10. Một phiên `VALIDATING/PROCESSING` tại một thời điểm (processing lease capacity=1). Demo chạy **đúng 1 worker**.
11. `REJECTED` là cuối, không retry. `FAILED` retry thủ công tối đa 2 lần; retry phải `try_acquire` lease **trước** khi tăng counter. Không bao giờ trả partial result.
12. Không đưa lời khuyên sửa/đàm phán vào prompt, response, export. Điều khoản có lợi hơn luật cho một role **không** là rủi ro của role đó.
13. Log/RunLog không chứa prompt, canonical/masked text, quote, PII, tên file thô.

## 4. Không làm (non-goals)

Chatbot, tài khoản/đăng nhập, missing-clause detection, OCR/scan, mobile, fine-tune/self-host model, graph DB, microservice, overlay highlight lên PDF/DOCX gốc, mật khẩu demo (chống lạm dụng bằng quota ngày + rate limit IP).

## 5. Pipeline một dòng

`Upload → Extraction → Scope precheck → PII masking → Segmentation → Clause Graph` (= VALIDATING) `→ Clause Classification [LLM#1] → Legal Retrieval (baseline + Data Graph 1-hop) → Risk Analysis [LLM#2] (+ Clause Graph context) → Citation validation → Assembly → COMPLETED` (= PROCESSING).

## 6. Từ điển nhanh

| Thuật ngữ | Nghĩa |
|---|---|
| Session | 1 lần làm việc = 1 role + 1 file. Đổi role/file = phiên mới. Không có `contract_id`/`analysis_id`. |
| Canonical text | Văn bản trích chuẩn hóa (NFC, LF) từ file gốc; hiển thị + highlight trên đây. |
| Masked text | Canonical đã thay PII bằng placeholder cùng độ dài (`<EMAIL>____`, tên 2 ký tự → `NN`). |
| Clause | Đơn vị điều khoản: `clause_id` (`cl_0001`…), `start_char`, `end_char`, `clause_labels` (1–3). |
| Clause taxonomy | 12 nhãn loại điều khoản (đóng băng MS-1). Semantics nguồn: data repo `clause_taxonomy_v03`; code: `taxonomy.py` (`TAXONOMY_VERSION=v04`, chỉ sửa định nghĩa prompt). Nguồn duy nhất trong code: `taxonomy.py`. |
| Risk taxonomy | Nhãn rủi ro kèm bảng severity theo (nhãn, `basis_type`, role). Tách biệt clause taxonomy. |
| `basis_type` | `LEGAL_VIOLATION` / `UNFAVORABLE` / `AMBIGUOUS`. Một giá trị cho mỗi clause, do LLM chọn. |
| Severity | `HIGH/MEDIUM/LOW`, `null` nếu thiếu căn cứ. Có thể khác nhau giữa 2 role. Backend tra bảng taxonomy, LLM không trả. |
| Evidence status | `SUPPORTED` / `INSUFFICIENT_EVIDENCE`. |
| Candidate | Điều luật ứng viên cho 1 clause (`citation_id` dạng `BLLD2019:art26`). |
| Data Graph | Nút = LegalProvision; cạnh `PARENT_OF`(AUTO) / `REFERS_TO`, `GUIDES`(MANUAL, đã xác minh). |
| Clause Graph | Nút = `clause_id`; cạnh `NEXT`, `PARENT_OF`, `REFERS_TO`. Xóa cùng phiên. |
| D1/D2/T1/T2 | Dev (BRD §8.2: 4 HĐ, 183 clause; data repo hiện có 5 HĐ / 234 clause — xem §12) / dev+lỗi chèn / test ≥10 HĐ / test+≥30 lỗi chèn. **Không chỉnh hệ thống dựa trên T1/T2.** |
| M1–M8, BL-1 | Chỉ số đánh giá (BRD §8.3). M5≥90% (≥30 lỗi chèn), M3a=100%, M4=100%, M1≥0.85, M2/M7≥0.80. |

## 7. State, lỗi, cấu hình tối thiểu

- State: `UPLOADED → VALIDATING → {REJECTED | FAILED | PROCESSING → {COMPLETED | FAILED}}`; `COMPLETED|FAILED|REJECTED → EXPIRED` (tombstone 24h rồi `SESSION_NOT_FOUND`).
- Lỗi không tạo session: `ROLE_REQUIRED(400)`, `SYSTEM_BUSY(409)`, `QUOTA_EXCEEDED(429)`, `RATE_LIMITED(429)`.
- Lỗi → `REJECTED` (đọc qua Get Status): `UNSUPPORTED_FILE_TYPE`, `FILE_TOO_LARGE`, `PDF_PAGE_LIMIT_EXCEEDED`, `DOCX_TEXT_LIMIT_EXCEEDED`, `NO_EXTRACTABLE_TEXT`, `UNSUPPORTED_TEXT_ENCODING`, `NOT_LABOR_CONTRACT`, `TOO_MANY_CLAUSES`.
- Lỗi → `FAILED`: `AI_TIMEOUT`, `AI_PROVIDER_ERROR`, `AI_OUTPUT_INVALID`, `INTERNAL_ERROR`. API-state: `INVALID_SESSION_STATE`, `SESSION_NOT_READY`, `SESSION_REJECTED`, `SESSION_EXPIRED(410)`, `RETRY_LIMIT_EXCEEDED`, `FEATURE_NOT_ENABLED(501)`, `SESSION_NOT_FOUND`.
- Mặc định: PDF ≤10MB/30 trang; DOCX ≤10MB/100.000 ký tự; `MAX_CLAUSES=150`; LLM timeout 30s, auto-retry ≤1 (chỉ timeout/network/429/5xx/schema-invalid; **không** retry 400/401/403); clause batch 20, risk batch 6, parallelism 2; `RETRIEVAL_SEED_K=3`, `RETRIEVAL_FINAL_K=8`; temperature 0.0. `DAILY_LLM_CALL_QUOTA` và `SESSION_CALL_RESERVE` **bắt buộc đặt ở demo, không dùng số 120** — chốt từ đo D1.

## 8. Quy ước code

- Python 3.12, FastAPI, Pydantic v2. Schema-first: sửa JSON Schema/Pydantic trước, mock sau, code sau cùng. Mọi schema có `schema_version`.
- Enum/nhãn có **một nguồn** trong code (`core/enums.py`, `clause/taxonomy.py`); enum trong JSON Schema được sinh từ đó hoặc có test đối chiếu (DEC-20).
- Chỉ **Orchestrator** đổi state. Stage module là hàm thuần, không import `api/` hay `session/`. Lỗi dùng typed exception (`ValidationReject`, `AiTimeout`, `AiProviderError`, `AiOutputInvalid`, `PipelineInternalError`, `LegalCorpusConflict`).
- Việc CPU nặng (PyMuPDF, DOCX, regex) chạy `asyncio.to_thread`/threadpool để polling status không bị chặn.
- Mỗi *actual* provider request (kể cả retry) tăng call counter + ghi cost. Eval harness gọi pipeline trực tiếp, bỏ qua quota/rate-limit nhưng ghi `eval_cost_ledger`.
- Test bằng `pytest`; mọi invariant INV-01…INV-12 (xem `SKELETON.md` §9) phải có test. Fixture có hợp đồng thật phải de-identify thủ công.
- Tiếng Việt cho message hiển thị người dùng; tên code/biến bằng tiếng Anh.

## 9. Trạng thái codebase (snapshot 12/10/2026 — chưa có frontend)

Codebase là **thiết kế tuần 1, lệch tài liệu**. Đừng phát triển tiếp trên schema cũ (`contract_id`, `type_scores`, `review_zone`) — các khái niệm này đã bị xóa khỏi `taxonomy`/schema (C-03, C-04 xong 20/10/2026); `clause_extraction_service.py` chỉ còn là cầu nối legacy. Danh sách thay đổi: `docs/splitted_docs/SRS/16_phu-luc-c-*.md` (C-01…C-21); kế hoạch thực hiện: `PROGRESS.md`; ánh xạ file cũ → file mới: `SKELETON.md` §2.
**Đã làm ở T1 (Người 1):** `backend/app/core/enums.py` + `backend/app/clause/taxonomy.py` (nguồn duy nhất, có `validate_labels`), `ai_pipeline/schemas/clause_output_v3.json`, test đối chiếu enum ↔ schema (`tests/contract/`, DEC-20); đã xóa `ai_pipeline/config/` và `clause_output_v2.json`.
**Đã làm ở T2 (Người 1, 25/10):** `backend/app/clause/structure_parser.py` (C-02) + `segmenter.py` (`segment()`, C-01 a; INV-02/03 có test), `backend/app/domain/errors.py` (`ValidationReject`), xóa `utils/text_processing.py` (`document_router`); freeze kỹ thuật clause taxonomy (`docs/CLAUSE_TAXONOMY_FREEZE.md`, `tests/unit/test_clause_taxonomy_freeze.py`; chính sách đa nhãn và 3 topic chưa có nhãn đang **chờ N2/N3**); CI `.github/workflows/ci.yml`.
Đã có (cần sửa): `ai_pipeline/services/clause_extraction_service.py` (legacy, thay phần phân loại ở C-01 b), `eval/eval_segmentation.py` (M1), `backend/app/services/document_service.py`, `services/llm_clients.py`, `api/routes/contracts.py`, backend Postgres/SQLAlchemy/Alembic, 3 adapter rỗng. Chưa có: DOCX, scope precheck, kho luật, retrieval, Data/Clause Graph, risk, export, RunLog/quota, frontend.

**Data (đối chiếu 17/10/2026, từ `DATA_LEAD_REVIEW_V03.md`):** data repo gắn submodule `ai_pipeline/data` ghim commit `a086606`; `clauses_v06.csv` = 234 clause / 5 HĐ / 4 template family (225 `EXACT` + 9 `CONTEXT`), giữ nguyên 183 annotation lịch sử; mỗi dòng một nhãn; `clause_text` không gồm heading. Chưa có gold rủi ro pháp lý; split dev/test mới là provisional và test đang nằm công khai trong repo. `synthetic_v0.2.json` (6 HĐ/27 clause) chỉ là smoke fixture. Smoke script `test_pipeline.py` đã chạy lại được sau C-03 (không còn `config.risk_routing`). `CLAUSE_TAXONOMY.md` và `DATA_PLAN.md` trong repo đã được thay bằng con trỏ + số liệu hiện hành (C-19 phần 1). **Đối chiếu 20/10:** `data.zip` mới nhận = release `v06-rc1` (hash khớp manifest, nhãn trùng `taxonomy.py`, số liệu khớp trên); có thêm 6 raw DOC/DOCX trong data repo và manifest ghi nguồn `5ce5796` — chưa xác nhận được tương ứng commit ghim `a086606` (chi tiết `docs/DATA_PLAN.md` §2a).

## 10. Tìm tài liệu nhanh (đừng đọc cả BRD/SRS/SDD/TDD)

```bash
python scripts/split_doc.py                 # tách (bỏ ảnh base64, ~205K ký tự thay vì ~370K)
python scripts/split_doc.py --find FR-12      # ID nằm ở file con nào
```
Bắt đầu từ `docs/splitted_docs/INDEX.md` và `docs/splitted_docs/ID_INDEX.md`. Tên file có thể đổi nếu thay `--max-chars`; khi đó dùng `--find`.

| Cần gì | Mở |
|---|---|
| HTTP API, request/response, lỗi API | `TDD/06_5-http-api-contract.md` |
| Domain model, JSON Schema, version pins | `TDD/07_6-domain-model-va-json-schema.md` |
| Orchestrator, state, retry/resume, lease | `TDD/08_7-analysis-orchestrator-*.md` |
| Extraction PDF/DOCX, canonical, quality gate | `TDD/09_8-document-processing-va-canonical-text.md` |
| Scope precheck / PII / Segmentation | `TDD/10_9-*`, `TDD/11_10-*`, `TDD/12_11-*` |
| Clause Graph / Classification LLM | `TDD/13_12-*`, `TDD/14_13-*` |
| Corpus, baseline retrieval, Data Graph | `TDD/15_14-legal-corpus-*.md` |
| Risk, citation validator, assembler | `TDD/16_15-risk-analysis-*.md` |
| Export / Ops, quota, security | `TDD/17_16-*`, `TDD/18_17-*` |
| Eval harness, test strategy | `TDD/19_18-*`, `TDD/20_19-*` |
| Cấu hình, `.env`, startup | `TDD/05_4-*`, `TDD/24_phu-luc-b-*` |
| Yêu cầu chức năng FR-01…FR-31 | `SRS/04_3-*`, `SRS/05_3-*` |
| Quyết định DEC-01…DEC-28 | `SRS/01_kiem-soat-tai-lieu.md` |
| Mã lỗi, state machine | `SRS/08_6-trang-thai-xu-ly-va-ma-loi.md` |
| Chỉ số M1–M8, dữ liệu D1/T1, nghiệm thu | `BRD/08_8-*` |
| Mốc MS-1…MS-5, thứ tự cắt, phân công | `BRD/09_9-*` |
| Open issues | `BRD/13_11-open-issues.md`, `SRS/15_13-*`, `TDD/22_21-*` |

## 11. Quy tắc làm việc cho AI

1. Đọc file này, rồi **chỉ** mở các file con liên quan tới task. Trích ID (FR-xx, DEC-xx, C-xx) trong câu trả lời/commit để truy vết.
2. Nếu yêu cầu của người dùng mâu thuẫn invariant §3: nói rõ mâu thuẫn và đề xuất sửa tài liệu, **không** lặng lẽ phá invariant.
3. Không bịa điều luật, số liệu, tên hàm đã "có" trong codebase. Chưa thấy code thì nói "chưa thấy", đừng giả định.
4. Giá trị cấu hình ghi "tune trên D1" được đổi **chỉ** dựa trên D1/D2, phải version config; không đổi dựa trên T1/T2.
5. Làm xong việc nào thì cập nhật `PROGRESS.md` (tick checkbox, ghi PR/commit). Việc thay đổi kiến trúc → cập nhật `ARCHITECTURE.md`/`SKELETON.md` cùng PR.

## 12. Điểm tài liệu còn lệch/mở (cần người quyết, đừng tự "sửa ngầm")

- BRD **BR-14** ghi "Cập nhật kho luật đòi hỏi sửa mã nguồn" nhưng BRD §6 (Bảo trì), SRS FR-24 yêu cầu **không** sửa mã → nhiều khả năng thiếu chữ "không"; cần chủ BRD xác nhận.
- SRS DEC-17 (bỏ `type_scores`, tier, `review_zone`) ghi "Không duyệt" ở cột người chốt; TDD vẫn dùng. Cần xác nhận chính thức (BRD OI-18).
- TDD 0.2 ghi cơ sở "SRS 1.3" trong khi SRS hiện là 1.4; API-state code của TDD §5.8 chưa backport vào SRS 6.2 (TDD O-09); SDD thiếu mũi tên `VALIDATING → FAILED` (TDD O-11).
- Chưa chốt: risk taxonomy (OI-01, hạn MS-1), phân công mảng chưa có chủ (OI-04), OI-03 SRS (ngưỡng scope precheck), OI-05 (quota/reserve), OI-10 (đa nhãn), OI-11 (đánh số DOCX tự động), OI-08 BRD (nghị định xử phạt mới từ 10/9/2026 chưa kiểm chứng → báo cáo **không nêu mức phạt**).
- **Data ↔ BRD §8.2:** BRD ghi D1 = 4 HĐ / 183 điều khoản; data repo hiện có 5 HĐ / 234 clause (183 là số annotation lịch sử được giữ). Chưa rõ D1 gồm HĐ/clause nào sau khi thêm dữ liệu → chủ BRD + Data Lead xác nhận rồi mới sửa BRD 8.2; **không tự sửa số trong BRD**.
- **Data ↔ T1/T2:** Data Lead ghi test đã nằm công khai trong repo, split mới là provisional, thiếu WORKING_TIME ở test và TERMINATION ở dev → chưa thỏa tinh thần T1 tách hoàn toàn khỏi dev/prompt (BRD 8.2) cho tới khi khóa split và giữ kín test.
- **Data ↔ nhãn:** topic bảo mật/không cạnh tranh và giải quyết tranh chấp chưa có nhãn/mapping được data v0.3 chốt (nhãn cũ `CONFIDENTIALITY_IP`, `DISPUTE_RESOLUTION` đã bỏ) → phải chốt trong annotation guideline **trước MS-1 (25/10)**. Quyền bồi thường của NLĐ đang rơi vào `OTHER` (C027).
- **Data ↔ đa nhãn:** dataset là single-label (đa nhãn = tách clause), còn SRS/BRD cho 1–3 nhãn/clause (OI-10 chưa freeze) → cần chính sách quy đổi gold ↔ prediction khi viết `load_dataset` (SKELETON §13).
- **Data ↔ segmentation:** dataset tách clause ngữ nghĩa bên trong Điều và bỏ heading, không phải partition → không dùng làm gold M1; 9 dòng `CONTEXT` không có span chính xác (TDD §18.3).
