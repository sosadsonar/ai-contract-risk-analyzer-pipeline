# PROGRESS.md — Kế hoạch 8 tuần xây dựng (12/10 → demo 06/12/2026) cho 5 thành viên

> Nguồn: BRD 0.5 §9 (mốc, thứ tự cắt, phân công), SRS 1.4 Phụ lục C (C-01…C-21), TDD 0.2 §20.2 (M0→M6), SDD 0.1.
> Đọc kèm: `AI_CONTEXT.md` (invariant, quy tắc), `SKELETON.md` (hàm/API; §2 ánh xạ file cũ→mới; §9 test INV), `ARCHITECTURE.md`.
> Tick `[x]` khi xong, ghi PR/commit sau mục. Đổi kế hoạch → ghi lý do ở §9 Nhật ký.

## 0. Đọc trước — giới hạn của bản kế hoạch này

1. **Phân công Người 1–5 là [Đề xuất]**. BRD §9.6 chỉ gán 5 mảng (Clause AI, Dữ liệu, Risk AI, Hệ thống, Giao diện) và để **chưa có chủ**: risk taxonomy (OI-01), PII masking (FR-10), dựng Data Graph + Clause Graph, harness đánh giá, pháp lý dữ liệu cá nhân (OI-03). Bản này gán các mảng đó cụ thể để cân tải; đề xuất nhóm chốt ở OI-04 ngay trong tuần 1.
2. **Tình trạng codebase lấy từ SRS/BRD Phụ lục C (snapshot 12/10/2026), chưa đối chiếu mã thật.** Snapshot **không có frontend** → phần giao diện (FR-19, FR-20, FR-25) chưa có đối chiếu.
3. Cỡ việc S/M/L là ước lượng thô của SRS Phụ lục C cho **một người, chưa gồm review**: S < 1 ngày, M 1–3 ngày, L > 3 ngày. Việc ngoài Phụ lục C (mã `X-xx` bên dưới) **chưa có cỡ** — nhóm tự ước lượng.
4. Ngày tuần: T1 12–18/10 · T2 19–25/10 · T3 26/10–1/11 · T4 2–8/11 · T5 9–15/11 · T6 16–22/11 · T7 23–29/11 · T8 30/11–6/12.
5. Quy tắc cứng: **không chỉnh hệ thống dựa trên T1/T2**; tuning chỉ trên D1/D2 và version config. **Không phát triển tiếp trên schema cũ** (`contract_id`, `type_scores`, `review_zone`).

## 1. Mốc

| Mốc | Ngày | Điều kiện đạt (rút gọn) | Nguồn |
|---|---|---|---|
| **MS-1** | 25/10 (hết T2) | Đóng băng clause taxonomy, risk taxonomy, severity rubric, annotation guideline; risk taxonomy có chủ + bản đầu; chốt danh mục kho luật tầng 1 | BRD §9.4, DEC-10, OI-01/02 |
| **MS-2** | 08/11 (hết T4) | Chốt cấu hình còn mở (SRS OI-03, 05, 09–12); kho luật tầng 1 bản đầu + Data Graph cấu trúc; pipeline chạy tới Clause Classification trên D1; che PII có số đo đầu trên D1 | BRD §9.4 |
| **MS-3** | 06/12 (hết T8) | Demo full luồng **cả hai vai trò**; khóa version hệ thống, ghi commit hash (EV-07) | BRD §9.4 |
| MS-4 | 13/12 (T9) | Chạy xong T1, T2, M1–M8, hiệu chuẩn judge (M6) | đề xuất, chờ OI-05 |
| MS-5 | 20/12 (T10) | Báo cáo đánh giá + bảo vệ | đề xuất |

Chạy song song T2→T8: **gán nhãn gold T1/T2** (từ sau MS-1, trước MS-4), không dùng gold để chỉnh hệ thống.

## 2. Phân công [Đề xuất]

| Người | Mảng chính | Việc code (C-xx) | Việc dữ liệu/khác (X-xx) |
|---|---|---|---|
| **N1** — Clause AI | Tách + phân loại điều khoản, LLM client, Clause Graph | C-01, C-02, C-03, C-04, **C-07**, **C-14**, C-19 (docs), M1/M7 trong C-18 | X-01 (cùng N2/N3: clause taxonomy + đa nhãn OI-10) |
| **N2** — Dữ liệu | Kho luật, retrieval, Data Graph, gold, harness | C-12, C-13, C-18 (runner + M3a/M4/M5/M8) | X-03, X-04, X-10 |
| **N3** — Risk AI | Risk taxonomy, **PII masking**, Risk LLM, citation | **C-09**, C-15, C-18 (M2/M6/BL-1) | X-01 (risk taxonomy + severity rubric), X-08, một phần X-05 |
| **N4** — Hệ thống | Extraction, phiên, API, ops, triển khai | C-05, C-06, C-08, C-10, C-11, C-16, C-17, C-20 | X-05, X-06, X-09 |
| **N5** — Giao diện | Frontend, highlight, báo cáo/export | **C-21** | X-02, X-07 |

Lý do chuyển so với BRD §9.6: C-07 (LLM client) từ N4 → N1 vì N1 là người dùng đầu tiên (LLM #1) và N4 đang nặng nhất về code; C-09 (PII, L) → N3 vì Risk AI chưa làm được nhiều trước khi có risk taxonomy + kho luật (T1–T3 còn rảnh); C-21 (export) → N5 vì BRD ghi "Giao diện, highlight, **báo cáo**". Độ lệch tải cần theo dõi: **N4 nặng code nhất**, **N2 nặng dữ liệu nhất** (kho luật + gold + lỗi chèn), **N5 phụ thuộc phạm vi frontend** (chưa ước lượng được).

## 3. Tồn kho công việc

### 3.1 CẦN SỬA — đang có trong codebase (theo Phụ lục C) — chi tiết file ở `SKELETON.md` §2

| ID | Thứ đang có | Làm gì | Cỡ | Người | Tuần |
|---|---|---|---|---|---|
| C-03 | `config/labeling.py`: `type_scores`, `max_content_risk_tier`, `review_zone`, 2 import hỏng | Xóa; chỉ còn validate 1–3 nhãn / thuộc taxonomy / không trùng | S | N1 | T1 |
| C-04 | `schemas/clause_output_v2.json` (`contract_id`, `taxonomy_version` cứng v02 trong khi `taxonomy.py` đã là v04, enum chép tay) | Tạo `clause_output_v3` + `risk_output_v1`; enum sinh từ code hoặc test đối chiếu; `taxonomy_version` = taxonomy nguồn data (v03), revision prompt v04 ghi qua `clause_prompt_version` (TDD §6.4). *SRS C-04 ghi "v03" là số cũ — sửa khi SRS có bản mới* | S | N1 (+N3 risk) | T1 |
| C-17 | `test_pipeline.py`, `test_llm_pipeline.py` (script tay), `pyproject` trỏ `tests/` chưa có, mock schema cũ | Chuyển pytest; viết test INV trước; mock theo schema mới | M | N4 | T1–T2 |
| C-20 | `pyproject.toml` thiếu deps backend; `requirements.txt` UTF-16 | Gộp 1 nguồn deps, UTF-8, thêm lib DOCX/export | S | N4 | T1 |
| C-01 | `clause_extraction_service.py`: 1 prompt LLM cắt+phân loại trên text chưa che; `_locate_span` | Tách `segment()` (local) + `classify()` (theo lô); bỏ `_locate_span`; giữ prompt từ `LABEL_DEFINITIONS` | M | N1 | T2–T4 |
| C-02 | `utils/text_processing.py`: `document_router` (tỉ lệ heading 0.40) | Bỏ router; regex trả khoảng; fallback paragraph; fixture ca dị | M | N1 | T2 |
| C-05 | Postgres + SQLAlchemy + Alembic; bảng `contracts` lưu `original_text` | In-memory store, UUID, TTL 60', lease capacity=1, 1 worker; sqlite chỉ metadata | M | N4 | T2 |
| C-06 | `api/routes/contracts.py`: chỉ `.pdf`, không role, `HTTPException` | 6 operation, admission gate, REJECTED async, role bắt buộc, PDF/DOCX | M | N4 | T2–T5 |
| C-07 | `services/llm_clients.py`: free tier + Qwen, timeout 60/120s, key trong query | Provider abstraction, Gemini paid, schema, timeout 30s, retry matrix, ledger, key qua header | M | N1 | T3 |
| C-08 | `document_service.py`: `get_text()` nối newline | NFC, reading order, header/footer/bảng, DOCX, legacy-font detector, threadpool | L | N4 | T3–T4 |
| C-11 | 3 adapter rỗng (`clause_ai`, `risk_ai`, `explanation_ai`) | Giữ 2 (classify, risk); xóa explanation; sửa `backend_architecture.md` | S | N4 | T3 |
| C-18 | `eval/eval_segmentation.py` chỉ có M1 | Giữ M1; thêm M2/M3a/M4/M5/M7/M8, privacy, judge, kappa, BL-1; eval ledger riêng | M | N2 (runner) + N1/N3 (metric) | T4–T7 |
| C-19 | `CLAUSE_TAXONOMY.md` (tier), `DATA_PLAN.md`, README, CONTRIBUTING, `text_extraction_contract.md` | Thay bằng con trỏ về BRD; giữ annotation guideline; sửa contract khớp SRS | S | N1 | T1, T7 |

### 3.2 CẦN THÊM — chưa có trong codebase

| ID | Hạng mục | Cỡ | Người | Tuần | Phụ thuộc |
|---|---|---|---|---|---|
| C-09 | PII masking local (placeholder cùng độ dài, privacy test, đo trên D1) | L | N3 | T2–T4 | gold privacy D1 (N2) |
| C-10 | Scope precheck HĐLĐ + fixture dương/âm | S | N4 | T3 | — |
| C-12 | Kho luật: format tách khỏi mã, validator fail-fast, retrieval nền, hiệu lực, citation check | L | N2 | T2–T5 | danh mục tầng 1 (MS-1) |
| C-13 | Data Graph in-memory (PARENT_OF auto, REFERS_TO/GUIDES verified), graph on/off cùng `final_k` | M | N2 | T4–T5 | C-12 |
| C-14 | Clause Graph (NEXT/PARENT_OF/REFERS_TO) + Context Resolver + trace ID-only | M | N1 | T4–T5 | C-01/02 |
| C-15 | Risk: prompt + candidate catalog + structured output + derive `risk_basis` + citation validate + advice lint | L | N3 | T4–T6 | risk taxonomy (MS-1), C-12 |
| C-16 | RunLog, quota/reserve, IP rate limit, eval ledger | M | N4 | T4–T6 | benchmark D1 |
| C-21 | Export DOCX (PDF = cut item 4), ReportModel | M | N5 | T3–T5 | `final_result_v1` |
| X-01 | Risk taxonomy (OI-01), severity rubric, annotation guideline, chính sách đa nhãn (OI-10); freeze | — | N3 (risk) + N1/N2 | T1–T2 | — |
| X-02 | Frontend (FR-19, 20, 25): upload, polling, highlight, kết quả, export, End, Retry | — | N5 | T1–T7 | mock API (N4, T1) |
| X-03 | Nội dung kho luật tầng 1 (provisions, edges verified, label_map) | — | N2 | T2–T5 | X-01 |
| X-04 | Gold D1/D2/T1/T2 + lỗi chèn ≥30 (mỗi role ≥10), ≥20% item gán đôi (kappa) | — | N2 lead, cả nhóm | T2–T8 (+T9) | MS-1 |
| X-05 | Benchmark D1 (p50/p90 từng stage) + cost model → chốt `DAILY_LLM_CALL_QUOTA`, `SESSION_CALL_RESERVE`, batch size | — | N4 + N3 | T4–T6 | C-07, pipeline chạy |
| X-06 | Hosting + HTTPS + 1 worker + smoke | — | N4 | T7 | chọn nhà cung cấp |
| X-07 | Disclaimer + data notice (BRD Phụ lục A) ở upload/kết quả/export | — | N5 | T1–T3 | — |
| X-08 | Judge calibration (M6), BL-1 (cut item 1 nếu trễ) | — | N3 | T6–T7 | gold T1 |
| X-09 | Test bảo mật: outbound capture, quét log PII, audit restart/temp | — | N4 | T5–T7 | — |
| X-10 | Thu ≥10 hợp đồng gốc cho T1 (PDF + DOCX, đa dạng), de-identify thủ công (BRD 7.6) | — | N2 + cả nhóm | **bắt đầu T2** | — |
| X-11 | Backport tài liệu: API-state code vào SRS 6.2 (TDD O-09), mũi tên `VALIDATING→FAILED` ở SDD (TDD O-11), xác nhận BR-14/DEC-17 | S | cả nhóm | T2 | — |

## 4. Kế hoạch từng tuần

### Tuần 1 (12–18/10) — Schema-first, khung dự án (TDD M0)
**Mục tiêu:** mọi mảng có schema mới + mock để làm song song.
- **N1**
  - [ ] C-04: `clause_output_v3.json`; `core/enums.py` + `clause/taxonomy.py` là nguồn duy nhất; test đối chiếu enum ↔ schema (DEC-20)
  - [ ] C-03: xóa `type_scores/tier/review_zone` + 2 import hỏng; `labeling.py` chỉ còn validate
  - [ ] Đọc `clause_extraction_service.py` thật, ghi **hiện trạng thực** (khác mô tả C-01 thì ghi §9)
  - [x] C-19 (phần 1a, 17/10 — chưa có PR): `CLAUSE_TAXONOMY.md`/`DATA_PLAN.md` đã thay bằng con trỏ về BRD 8.2 + số liệu data v06; giữ annotation guideline
  - [x] C-19 (phần 1b, 17/10 — chưa có PR): `README.md`, `CONTRIBUTING.md` (cây thư mục, §3, §7, cảnh báo free tier), `text_extraction_contract.md` (bỏ DOC/`review_zone`/DB, gộp 2 đoạn `extraction_version`, offset code point, masked text) đã khớp SRS/TDD
  - [ ] C-19 (phần 2, T7): `CONTRIBUTING.md` §1–§3 (provider/`.env`, cách chạy test) viết lại khi C-07/C-17 xong
- **N2**
  - [ ] Định dạng corpus (`manifest.yaml`, `provisions.jsonl`, `edges.jsonl`, `label_map.yaml`) + 3–5 provision mẫu cho dev
  - [ ] Bản nháp **danh mục kho luật tầng 1** (OI-02) để chốt ở MS-1
  - [ ] Kiểm kê D1 (BRD 8.2: 4 HĐ, 183 clause): còn PII không, đã de-identify chưa; **đối chiếu với data repo v06 (5 HĐ / 234 clause, 183 annotation lịch sử)** và chốt D1 gồm HĐ nào (không tự sửa BRD)
- **N3**
  - [x] X-01: bản đầu **risk taxonomy** theo role, mỗi nhãn có `basis_type` (LEGAL_VIOLATION/UNFAVORABLE/AMBIGUOUS); nháp severity rubric
  - [x] `risk_output_v1.json` 
  - [ ] + (cùng N4) `final_result_v1.json`
  - [x] pre C-09: Spike PII: danh sách pattern regex tiếng Việt (email, SĐT, CCCD, TK ngân hàng)
- **N4**
  - [ ] C-17: pytest chạy được (`tests/{unit,integration,contract,fixtures}`, sửa `testpaths`), CI chạy pytest
  - [ ] Dựng cây package `backend/app/*` theo TDD §3.2 (file rỗng/stub), `core/config.py`
  - [ ] **Mock API 6 operation theo schema mới** (thay `mock_clause_service.py`) để N5 làm UI
  - [ ] C-20: một nguồn deps, UTF-8, thêm python-docx/lxml/rank-bm25
- **N5**
  - [ ] Chọn framework (đề xuất React + TS + Vite), dựng skeleton `frontend/`; `api/types` theo mock
  - [ ] `lib/offset.ts` (code point → UTF-16) + test non-BMP (INV-12)
  - [ ] X-07: soạn disclaimer + data notice từ BRD Phụ lục A
  - [ ] Trang Upload (role bắt buộc) chạy với mock

**Cổng T1:** schema mới merge; mock chạy; không ai code trên schema cũ; `pytest` xanh; OI-04 (phân công) chốt.

### Tuần 2 (19–25/10) — MS-1: đóng băng taxonomy; bắt đầu phiên/API + tiền xử lý (TDD M1, M2)
- **N1**
  - [ ] C-02: `structure_parser` (5 pattern), bỏ `document_router`, fallback paragraph; fixture `nested_article_subclauses`, `paragraph_fallback`
  - [ ] C-01 (a): `segment()` v1 theo partition không chồng lấn (INV-02/03), chưa cần PII thật
  - [ ] **Freeze** clause taxonomy + chính sách đa nhãn (OI-10) cùng N2/N3 — gồm chốt topic bảo mật/không cạnh tranh và giải quyết tranh chấp (hiện chưa có nhãn) và quyền bồi thường NLĐ (đang là `OTHER`)
- **N2**
  - [ ] **Freeze** annotation guideline; **chốt danh mục tầng 1** (MS-1)
  - [ ] X-03: nhập provisions tầng 1 đợt 1 + `label_map` v0
  - [ ] X-10: bắt đầu thu hợp đồng T1; quy trình de-identify
- **N3**
  - [ ] **Freeze** risk taxonomy + severity rubric (MS-1) — cả nhóm review
  - [x] C-09 (a): `pii_types`, `mask_value`, `detector` regex (email, SĐT, CCCD, TK NH)
  - [ ] **INV-01** test
- **N4**
  - [ ] C-05: `InMemorySessionStore`, `ProcessingLease`, state machine; **test barrier 2 Create đồng thời**
  - [ ] C-06 (a): `admission_gate` (role → rate → quota → lease), 6 route trả state thật; chốt cách làm **hard byte cap** (SKELETON §3)
  - [ ] `ops/metadata_db.py` (sqlite metadata-only)
  - [ ] X-11: backport tài liệu (O-09, O-11)
- **N5**
  - [ ] `usePolling` (500 ms → 1,5 s → 2,5 s), catalog thông báo lỗi (TDD Phụ lục E)
  - [ ] Trang Progress + Result (layout) trên mock `final_result_v1`; highlight dùng offset map

**Cổng MS-1 (25/10):** 4 artifact (clause taxonomy, risk taxonomy, severity rubric, annotation guideline) đã đóng băng; risk taxonomy có người phụ trách; danh mục kho luật tầng 1 chốt.

### Tuần 3 (26/10–1/11) — Tiền xử lý cục bộ chạy được trên D1
- **N1**
  - [ ] C-01 (b): `segment()` hoàn chỉnh — `boundary_guard` với `pii_spans`, ≤150 clause (`TOO_MANY_CLAUSES`), warning clause >4000 ký tự; INV-02/03 pass
  - [ ] C-07: `LLMProvider`, `GeminiProductClient` (paid, `response_schema`, timeout 30s, retry matrix, key qua header), `CallLedger`; `DevLocalClient` chỉ dev
  - [ ] `ai/prompts/clause_v1.py` (sinh từ taxonomy); `clause_adapter` khung với provider mock
- **N2**
  - [ ] C-12 (a): `corpus_loader`, `corpus_validator` (overlap hiệu lực, endpoint cạnh, PARENT_OF acyclic) + fixture `valid/`, `invalid_overlap/`, `invalid_edge/`
  - [ ] X-03: provisions tầng 1 đủ để baseline chạy
  - [ ] X-04: bắt đầu gold segmentation D1 (sửa tay ranh giới) để đo M1 — dataset v06 là gold nhãn clause (1 dòng/1 nhãn, bỏ heading, 9 dòng `CONTEXT` `span=null`), **không** dùng làm gold M1; viết adapter v06 → `clause.json` (TDD §18.3) và policy `CONTEXT` trước khi tính F1
- **N3**
  - [ ] C-09 (b): heuristic tên / pháp nhân / địa chỉ / ngày sinh, preserve-list, resolve overlap
  - [ ] Phối hợp N1 tích hợp `boundary_guard` ↔ `pii_spans`; fixture `privacy/`
  - [ ] Gold privacy D1 (cùng N2) để đo BRD 7.3
- **N4**
  - [ ] C-08 (a): PDF extractor (PyMuPDF, 2 cột, header/footer ≥60% trang, bảng `|`), `canonicalizer`, `quality` (gồm **legacy-font TCVN3/VNI** với fixture phải fail)
  - [ ] C-10: scope precheck + fixture dương/âm (OI-03: ngưỡng tune trên D1)
  - [ ] C-11: xóa `explanation_ai`, sửa `backend_architecture.md`
  - [ ] Nối thật `VALIDATING`: extract → scope → mask → segment (stage chưa xong thì stub)
- **N5**
  - [ ] Result page highlight thật trên mock; nút Retry/End; đủ nhánh REJECTED/FAILED/EXPIRED
  - [ ] C-21 (a): `build_report_model` trên mock

**Cổng T3:** PDF → canonical → mask → segment chạy end-to-end cục bộ trên D1 (chưa gọi LLM); INV-01/02/03 xanh.

### Tuần 4 (2–8/11) — MS-2: tới Clause Classification trên D1
- **N1**
  - [ ] `classify_clauses` đầy đủ: batch (20), song song (2), kiểm cancel giữa batch, validate (mỗi ID đúng 1 lần, 1–3 nhãn), retry ≤1 → `AI_OUTPUT_INVALID`; **INV-05** (response có field lạ bị từ chối)
  - [ ] Chạy trên D1 (Gemini paid, dữ liệu đã che); đo sơ bộ M1, M7
  - [ ] C-14 (a): `graph_builder` NEXT + PARENT_OF; **INV-08**
- **N2**
  - [ ] C-12 (b): `BaselineRetriever` (label_map + BM25 `0.70/0.30`, hiệu lực, dedupe, seed/pool)
  - [ ] C-13 (a): Data Graph cấu trúc (PARENT_OF tự sinh) + REFERS_TO/GUIDES verified đợt 1
  - [ ] Kho luật tầng 1 bản đầu; gold clause labels D1
- **N3**
  - [ ] **Báo cáo số đo PII đầu tiên trên D1** (recall theo nhóm + preserve rate vs BRD 7.3); nếu không đạt → quyết định local NER (OI-12) tại MS-2
  - [ ] Thiết kế prompt `risk_v1` + khung `risk_adapter` với provider mock
- **N4**
  - [ ] C-08 (b): DOCX extractor (numbering, tracked changes accepted-state, textbox); phạm vi numbering (OI-11)
  - [ ] C-16 (a): `RunLogWriter`, `DailyQuota.before_call/after_call` (tăng nguyên tử **trước** call), `EvalCostLedger` khung
  - [ ] X-05 (a): bộ đo benchmark D1 (p50/p90 từng stage)
  - [ ] **Họp chốt cấu hình mở:** SRS OI-03, 05, 09–12
- **N5**
  - [ ] Ghép frontend với backend thật tới trạng thái PROCESSING; polling ≤2 s hiển thị VALIDATING/PROCESSING
  - [ ] Catalog lỗi đầy đủ theo `error_code`

**Cổng MS-2 (08/11):** pipeline tới Clause Classification chạy trên D1; kho luật tầng 1 bản đầu + Data Graph cấu trúc; PII có số đo đầu; cấu hình mở đã chốt.

### Tuần 5 (9–15/11) — Retrieval + Risk + Clause Graph (TDD M4, M5)
- **N1**
  - [ ] C-14 (b): `REFERS_TO` (regex) **loại trừ dẫn chiếu pháp luật**; `resolve_context` (≤3 clause, ≤6000 code point); `ContextResolutionTrace`; fixture `refers_contract`, `excludes_legal_reference`
  - [ ] Tuning classification trên D1/D2 (version config)
- **N2**
  - [ ] C-13 (b): `DataGraph.expand` + `get_candidates` (seed-first, merge, **cùng `final_k`**; lỗi runtime → fallback + `graph_fallback`); **INV-11**
  - [ ] Tuning `label_map`/trọng số trên D1/D2
  - [ ] X-04: D2 lỗi chèn (dev, tách quy định khỏi T2); gold seg T1 cho hợp đồng đã thu
- **N3**
  - [ ] C-15 (a): `risk_adapter` đầy đủ (candidate catalog dedupe, related context, structured output, batch 6); `detect_advice` (theo cụm, không match "nên" đơn), `detect_unsupported_reference`, `sanitize_explanation`
  - [ ] `citation_validator` (INV-06); `derive_risk_basis` + `assemble` (INV-07)
- **N4**
  - [ ] Nối thật `PROCESSING` trong orchestrator; **retry/resume** (`failed_stage` → VALIDATING/PROCESSING, fingerprint; trễ thì cắt item 2); cancel; test End vs callback muộn
  - [ ] `cleanup` + tombstone 24h; route `export`; **INV-09/10**
  - [ ] C-16 (b): `SlidingWindowLimiter` (HMAC IP)
- **N5**
  - [ ] C-21 (b): `export_docx` đủ quote, risk + basis, severity/"chưa đủ căn cứ", explanation, citation, disclaimer, **data notice**
  - [ ] UI: `INSUFFICIENT_EVIDENCE` (không badge severity), không risk ("Không phát hiện rủi ro trong phạm vi phân tích")

**Cổng T5:** test tích hợp toàn pipeline với LLM mock xanh; INV-01…11 có test; DOCX xuất được.

### Tuần 6 (16–22/11) — Chạy thật cả hai vai trò, đo chi phí/hiệu năng
- **N1**
  - [ ] Pipeline thật (Gemini paid) trên D1 cho cả 2 vai trò; sửa lỗi segmentation/classification
  - [ ] `metrics/segmentation.py` (M1), `metrics/clause_classification.py` (M7)
- **N2**
  - [ ] `runner.py` + `load_dataset`; `metrics/citation_validity.py` (M3a), `quote_span.py` (M4), `injected_recall.py` (M5), `retrieval.py` (M8 on/off, predicted labels primary)
  - [ ] X-04: bắt đầu **T2** — chèn lỗi (mục tiêu ≥30, mỗi role ≥10), 2 người xác minh mỗi lỗi
- **N3**
  - [ ] Chạy M5/M8 trên D2 (dev) để tune lint + prompt (version prompt)
  - [ ] `metrics/risk_classification.py` (M2); X-08 khung judge (M6)
  - [ ] Với N4: chốt `DAILY_LLM_CALL_QUOTA`, `SESSION_CALL_RESERVE` = p95 planned calls (OI-05)
- **N4**
  - [ ] X-05: benchmark D1 hoàn chỉnh (kể cả provider latency injection); chốt batch size/parallelism
  - [ ] X-09: **INV-04** outbound capture; quét log tìm PII; audit DB/temp/restart
  - [ ] Test API/state đầy đủ (TDD §19.3)
- **N5**
  - [ ] E2E UI với backend thật; kiểm tra non-BMP trong trình duyệt (**INV-12**)
  - [ ] Soát disclaimer + data notice ở upload/kết quả/export (FR-25)

**Cổng T6:** chạy thật full luồng cả 2 vai trò trên D1; đã có p50/p90 và cost model; quota/reserve có số.

### Tuần 7 (23–29/11) — Ổn định, harness hoàn chỉnh, triển khai
- **N1**
  - [ ] C-19 (phần 2): `text_extraction_contract.md` khớp SRS; README/CONTRIBUTING trỏ về BRD
  - [ ] Bug bash segmentation/classification trên D1/D2
- **N2**
  - [ ] Dry-run `runner` trên D1/D2 (không đụng T1/T2 để tuning)
  - [ ] Hoàn tất lỗi chèn T2 + gold; ghim `corpus_version`, `data_graph_version`
- **N3**
  - [ ] X-08: hiệu chuẩn judge (M6 ≥80% & κ≥0.6) trên mẫu 40; BL-1 (nếu chưa cắt)
  - [ ] Ghim `risk_prompt_version`, `severity_rubric_version`
- **N4**
  - [ ] X-06: hosting + HTTPS + **đúng 1 worker** (smoke fail nếu >1) + chốt biến môi trường demo
  - [ ] Tối ưu hiệu năng nếu p90 >120s (giảm payload/tăng batch/giảm context trước, không đổi invariant)
  - [ ] Test fail-fast khi thiếu `GEMINI_MODEL_ID`/quota/reserve ở demo
- **N5**
  - [ ] Hoàn thiện UI, thông điệp lỗi, kịch bản demo; export DOCX kiểm lần cuối
  - [ ] (nếu còn thời gian) PDF export — **cut item 4**, cần chủ BRD duyệt nếu bỏ

**Cổng T7:** đã triển khai chạy được; harness chạy đủ M1–M8 trên D1/D2; checklist TDD Phụ lục D còn ≤ vài mục.

### Tuần 8 (30/11–6/12) — Khóa phiên bản, demo MS-3
- **Cả nhóm**
  - [ ] Chạy **checklist TDD Phụ lục D** (schema, privacy, span M4=100%, corpus, graph, LLM, state, performance, cost, deployment, no-persistence, export, frontend, eval, locked test)
  - [ ] Chỉ sửa lỗi, **không đổi prompt/config** ngoài allowlist sau khi khóa; ghi **commit hash + version pins** (EV-07)
  - [ ] Diễn tập demo 2 vai trò (EMPLOYEE, EMPLOYER) trên cùng hợp đồng; có file dự phòng (video/ảnh chụp)
- **N1/N2/N3:** bug bash phần của mình; xác nhận version pin (taxonomy, corpus, prompt)
- **N4:** runbook triển khai, smoke test cuối, kiểm tra restart xóa session
- **N5:** bản demo UI + kịch bản trình bày

**Cổng MS-3 (06/12):** demo full luồng cả hai vai trò; commit hash đã ghi.

## 5. Tuần 9–10 (đánh giá — ngoài 8 tuần xây dựng; chi tiết `BRD/08_8-*`)

- T9 → **MS-4 (13/12):** chạy T1 (M1, M2, M3a, M3b, M4, M6, M7, BL-1) + T2 (M5, M8; graph on/off cùng `final_k`); ngân sách đánh giá $15 qua `eval_cost_ledger`.
- T10 → **MS-5 (20/12):** báo cáo (nêu giới hạn: gold không có luật sư, M5 là recall trên rủi ro có căn cứ rõ, **không nêu mức phạt** do BRD OI-08) + bảo vệ.

## 6. Quyết định cần người chốt (đừng tự "sửa ngầm")

| Việc | Hạn | Ai |
|---|---|---|
| OI-04 phân công mảng chưa có chủ (xác nhận §2) | T1 | cả nhóm |
| OI-01 risk taxonomy có chủ + bản đầu | T1–T2 (MS-1) | N3 |
| OI-10 chính sách đa nhãn (1–3 nhãn, ưu tiên 1) — freeze cùng guideline; kèm quy tắc quy đổi dataset single-label ↔ prediction đa nhãn | MS-1 | N1 + N2 |
| D1 trong BRD 8.2 (4 HĐ/183) lệch data repo hiện tại (5 HĐ/234, 183 annotation lịch sử) — xác nhận thành phần D1 rồi mới sửa BRD | T2 | chủ BRD + N2 |
| Test split đang công khai trong repo, mới provisional; thiếu WORKING_TIME (test) / TERMINATION (dev) — khóa split, giữ kín T1 | trước MS-4 | N2 |
| Topic bảo mật/không cạnh tranh, giải quyết tranh chấp chưa có nhãn data v0.3 chốt — đưa vào annotation guideline | MS-1 | N1 + N2 |
| BRD **BR-14** ghi "cập nhật kho luật đòi hỏi sửa mã nguồn" mâu thuẫn FR-24/BRD §6 → có thể thiếu chữ "không" | T2 | chủ BRD |
| SRS **DEC-17** (bỏ `type_scores`, tier, `review_zone`) cột người chốt ghi "Không duyệt" trong khi TDD vẫn dùng (BRD OI-18) | T2 | chủ SRS |
| SRS OI-03 (ngưỡng scope precheck), OI-05 (quota/reserve), OI-11 (đánh số DOCX), OI-12 (local NER) | MS-2 | cả nhóm |
| Cách hiện thực hard byte cap khi upload; ý nghĩa `progress.total_units`; mã HTTP của retry (`SKELETON.md` §13) | T2 | N4 |
| BRD OI-03 pháp lý dữ liệu cá nhân gửi ra nước ngoài (chưa xác nhận) | trước demo | cả nhóm |

## 7. Thứ tự cắt khi trễ (BRD §9.5 — cắt từ trên xuống, không nhảy bước)

1. BL-1 (so với LLM thông dụng)
2. Stage resume → retry chạy lại từ đầu, vẫn giữ giới hạn 2 lần
3. LLM hỗ trợ tách điều khoản → chỉ luật + fallback paragraph (hiện đã là mặc định)
4. Export PDF → chỉ DOCX (**cần chủ BRD duyệt**, vì BR-02 yêu cầu cả hai)
5. Graph → chỉ giữ cạnh cấu trúc, bỏ `REFERS_TO`/`GUIDES` (**cần chủ BRD + giảng viên duyệt**; Data Graph và Clause Graph vẫn phải có — BR-17, BR-18)

## 8. Đường găng và rủi ro tiến độ

| Chuỗi phụ thuộc | Rủi ro | Biện pháp |
|---|---|---|
| risk taxonomy (MS-1) → `risk_adapter` (C-15) → `derive_risk_basis` | OI-01 chưa có chủ ⇒ N3 bị chặn từ T4 | Chốt chủ ở T1, bản đầu ở T1–T2 |
| danh mục tầng 1 → corpus → baseline → Data Graph → M8 | Kho luật sai/thiếu, không có luật sư | Closed corpus + `INSUFFICIENT_EVIDENCE`, edges chỉ load khi đã verified |
| C-08 (L) extraction → segmentation → toàn bộ pipeline | N4 nặng nhất | Mock/fixture canonical để N1/N3 không phải chờ; C-07 đã chuyển cho N1 |
| C-09 (L) PII → `boundary_guard` → INV-03 | PII recall không đạt BRD 7.3 | Đo sớm trên D1 (T4); local NER chỉ thêm nếu D1 không đạt (OI-12) |
| X-10 thu T1 (≥10 hợp đồng gốc) | Chưa rõ nguồn hợp đồng; de-identify tốn công | Bắt đầu T2; nếu thiếu, báo sớm vì mọi chỉ số đo trên T1 phụ thuộc vào đây |
| X-05 benchmark → quota/reserve (OI-05) | Số đo đến muộn ⇒ không khóa được cấu hình demo | Benchmark chạy từ T4, chốt ở T6 |
| Frontend chưa có đối chiếu (X-02) | Phạm vi chưa ước lượng | N5 làm trên mock từ T1; checkpoint với N4 mỗi tuần |

## 9. Nhật ký (ghi khi làm xong / khi kế hoạch đổi)

| Ngày | Người | Việc / PR / commit | Ghi chú (sai khác so với mô tả Phụ lục C, đổi kế hoạch…) |
|---|---|---|---|
| 2026-10-13 | — | Tạo `AI_CONTEXT.md`, `ARCHITECTURE.md`, `split_doc.py`, `SKELETON.md`, `PROGRESS.md` | Snapshot codebase chưa có frontend; Phụ lục C chưa đối chiếu mã thật |
