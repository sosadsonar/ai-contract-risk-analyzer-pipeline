# PROGRESS.md — Kế hoạch 8 tuần xây dựng (12/10 → demo 06/12/2026) cho 5 thành viên

> Nguồn: BRD 0.6 §9 (mốc, thứ tự cắt, phân công), SRS 1.5 Phụ lục C (C-01…C-21), TDD 0.3 §20.2 (M0→M6), SDD 0.2. Cập nhật 03/11/2026 sau audit tài liệu (bộ 5 patch `cra-doc-patches.zip`): việc mới mã X-12 đến X-29; các mục đã tick giữ nguyên.
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
| **N1** — Clause AI | Tách + phân loại điều khoản, LLM client, Clause Graph | C-01, C-02, C-03, C-04, **C-07**, **C-14**, C-19 (docs), M1/M7 trong C-18 | X-01 (cùng N2/N3: clause taxonomy + đa nhãn OI-10); X-20 (`boundary_guard`), X-21, X-27 (metric M10) |
| **N2** — Dữ liệu | Kho luật, retrieval, Data Graph, gold, harness | C-12, C-13, C-18 (runner + M3a/M4/M5/M8) | X-03, X-04, X-24, X-25, X-26, X-27 (dữ liệu D3), X-29; X-10 chuyển sang N5 (O-06) |
| **N3** — Risk AI | Risk taxonomy, **PII masking**, Risk LLM, citation | **C-09**, C-15, C-18 (M2/M6/BL-1) | X-01 (risk taxonomy + severity rubric), X-08, một phần X-05; X-12, X-15, X-16 (risk), X-17, X-18, X-22, X-28 |
| **N4** — Hệ thống | Extraction, phiên, API, ops, triển khai | C-05, C-06, C-08, C-10, C-11, C-16, C-17, C-20 | X-05, X-06, X-09; X-13, X-16 (final_result), X-19, X-20 |
| **N5** — Giao diện | Frontend, highlight, báo cáo/export | **C-21** | X-02, X-07; X-10 (nhận từ N2), X-14, X-23 |

Lý do chuyển so với BRD §9.6: C-07 (LLM client) từ N4 → N1 vì N1 là người dùng đầu tiên (LLM #1) và N4 đang nặng nhất về code; C-09 (PII, L) → N3 vì Risk AI chưa làm được nhiều trước khi có risk taxonomy + kho luật (T1–T3 còn rảnh); C-21 (export) → N5 vì BRD ghi "Giao diện, highlight, **báo cáo**". Độ lệch tải cần theo dõi: **N4 nặng code nhất**, **N2 nặng dữ liệu nhất** (kho luật + gold + lỗi chèn), **N5 phụ thuộc phạm vi frontend** (chưa ước lượng được).

## 3. Tồn kho công việc

### 3.1 CẦN SỬA — đang có trong codebase (theo Phụ lục C) — chi tiết file ở `SKELETON.md` §2

| ID | Thứ đang có | Làm gì | Cỡ | Người | Tuần |
|---|---|---|---|---|---|
| C-03 | `config/labeling.py`: `type_scores`, `max_content_risk_tier`, `review_zone`, 2 import hỏng | Xóa; chỉ còn validate 1–3 nhãn / thuộc taxonomy / không trùng | S | N1 | T1 |
| C-04 | `schemas/clause_output_v2.json` (`contract_id`, `taxonomy_version` cứng v02 trong khi `taxonomy.py` đã là v04, enum chép tay) | Tạo `clause_output_v3` + `risk_output_v2`; enum sinh từ code hoặc test đối chiếu; `taxonomy_version` = taxonomy nguồn data (v03), revision prompt v04 ghi qua `clause_prompt_version` (TDD §6.4). *SRS C-04 ghi "v03" là số cũ — sửa khi SRS có bản mới* | S | N1 (+N3 risk) | T1 |
| C-17 | `test_pipeline.py`, `test_llm_pipeline.py` (script tay), `pyproject` trỏ `tests/` chưa có, mock schema cũ | Chuyển pytest; viết test INV trước; mock theo schema mới | M | N4 | T1–T2 |
| C-20 | `pyproject.toml` thiếu deps backend | Gộp 1 nguồn deps, thêm lib DOCX/export | S | N4 | T1 |
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
| C-15 | Risk: prompt + candidate catalog + structured output + dựng `risk_basis` + tra severity + citation validate + advice lint | L | N3 | T4–T6 | risk taxonomy (MS-1), C-12 |
| C-16 | RunLog, quota/reserve, IP rate limit, eval ledger | M | N4 | T4–T6 | benchmark D1 |
| C-21 | Export DOCX (PDF = cut item 4), ReportModel | M | N5 | T3–T5 | `final_result_v1` |
| X-01 | Risk taxonomy (OI-01), severity rubric, annotation guideline, chính sách đa nhãn (OI-10); freeze | — | N3 (risk) + N1/N2 | T1–T2 | — |
| X-02 | Frontend (FR-19, 20, 25): upload, polling, highlight, kết quả, export, End, Retry | — | N5 | T1–T7 | mock API (N4, T1) |
| X-03 | Nội dung kho luật tầng 1 (provisions, edges verified, label_map) | — | N2 | T2–T5 | X-01 |
| X-04 | Gold D1/D2/T1/T2 + lỗi chèn ≥30 (mỗi role ≥10), ≥20% item gán đôi (kappa) | — | N2 lead, cả nhóm | T2–T8 (+T9) | MS-1 |
| X-05 | Benchmark D1 (p50/p90 từng stage) + cost model → chốt `DAILY_LLM_CALL_QUOTA`, `SESSION_CALL_RESERVE`, batch size | — | N4 + N3 | T4–T6 | C-07, pipeline chạy |
| X-06 | Hosting + HTTPS + 1 worker + smoke (hiện chạy localhost; chỉ làm nếu nhóm chọn hosting) | — | N4 | T7 | chọn nhà cung cấp |
| X-07 | Disclaimer + data notice (BRD Phụ lục A) ở upload/kết quả/export | — | N5 | T1–T3 | — |
| X-08 | Judge calibration (M6), BL-1 (cut item 1 nếu trễ) | — | N3 | T6–T7 | gold T1 |
| X-09 | Test bảo mật: outbound capture, quét log PII, audit restart/temp | — | N4 | T5–T7 | — |
| X-10 | Tiếp nhận 10 tài liệu theo `T1_EQUIVALENT_GATE_V1`: 4 bản thực/nội bộ hạn chế, 5 mẫu công khai, 1 đối chứng tổng hợp; quản lý PII cục bộ và báo riêng 3 lát cắt | — | N5 nhận từ N2 (O-06; N2 hướng dẫn nguồn) + cả nhóm | **bắt đầu T2** | BRD 0.6 §8.2; ADR cổng tương đương |
| X-11 | Ghi nhận sai khác O-09/O-11 và BR-14 trong nhật ký §9; tài liệu BRD/SRS/SDD/TDD đang freeze, chưa sửa baseline; DEC-17 chờ nhóm duyệt | S | cả nhóm | T2 | Nhóm duyệt errata/DEC-17 |
| X-12 | Áp bộ 5 patch tài liệu (BRD 0.6, SRS 1.5, SDD 0.2, TDD 0.3, ARCHITECTURE + SKELETON); chỉ định chủ biên từng tài liệu; sinh lại `docs/splitted_docs/` bằng `scripts/split_doc.py` | S | N3 áp, cả nhóm review | T4 (hạn 05/11) | patch |
| X-13 | Khóa chữ ký hàm + schema (SKELETON §13.1); sau mốc này đổi chữ ký cần PR có lý do và báo cả nhóm | — | N4 + cả nhóm | 05/11 | X-12, X-15, X-16 |
| X-14 | Vẽ lại ảnh pipeline và state machine trong SRS/SDD từ Mermaid ở ARCHITECTURE §2 (thay `pipeline.png`, `state_machine.png`) | S | N5 | T4–T5 | X-12 |
| X-15 | PR taxonomy một lần: đổi nhãn `POST_EMPLOYMENT_RESTRICTION` → `IP_CONFIDENTIALITY_NONCOMPETE` (doc, `taxonomy.py`, 2 schema, `labels.ts`, `mock.ts`, hằng fingerprint + version trong test), đổi cột "Căn cứ (candidate)" → "Căn cứ tham khảo", rà bảng severity (8 ô LV=MEDIUM; ô UF của NSDLĐ theo E1–E3), rồi freeze lại (freeze 25/10 đã tick được mở lại, xem §9) | M | N3 | T4 | — |
| X-16 | Schema: thêm trường tùy chọn `related_clause_ids` vào `risk_output_v2`; `clause` và `related_clause_ids` vào `final_result_v1` (không đổi version); test contract | S | N3 (risk) + N4 (final_result) | T4 | X-12 |
| X-17 | PII mở rộng: thêm TAX_ID, ID_ISSUE, BUSINESS_ADDRESS, SIGNATURE vào `pii_types.py` + detector; preserve-list (chức vụ đại diện NSDLĐ, tên tỉnh khi đứng riêng); tên pháp nhân che nguyên cụm; địa chỉ cư trú che cả tỉnh (BRD 7.2) | M | N3 | T4–T5 | X-12 |
| X-18 | Tập P1 (gold PII): script sinh PII giả chèn vào hợp đồng đã de-identify; ≥100 mẫu mỗi loại nhóm 99%, ≥50 mỗi loại nhóm 90%; mẫu âm; lỗi trích PDF (xuống dòng, khoảng trắng giữa chữ số, NFD); bộ sinh tách khỏi regex masker | M | N3 | T4–T5 | X-17 |
| X-19 | `backend/app/pipeline.py`: `analyze()` chạy chuỗi stage (hai móc `on_stage`, `check_cancel`, tham số `stop_after`, trả artifact từng stage); orchestrator và harness cùng gọi; bọc `session/local_validation.py` cho phần cục bộ | M | N4 | T5 | C-08(a), C-14(a) |
| X-20 | Sửa nhỏ mã: chuyển fixture `mock_final_result_v1.json` cạnh `session/mock.py` (đang đọc từ `tests/`); `_ALLOWED` thêm VALIDATING→EXPIRED và PROCESSING→EXPIRED; retry AI đặt stage theo `failed_stage`; N1 chuyển `boundary_guard` về `clause/segmenter.py` (SKELETON §5.6); xác nhận quota ngày lưu bền | S | N4 + N1 | T4–T5 | — |
| X-21 | Context Resolver cấp thêm clause JOB_INFO và CONTRACT_TERM_TYPE làm context chung (FR-33); Risk prompt điền `related_clause_ids` khi hai clause mâu thuẫn (FR-32) | S | N1 (Resolver) + N3 (prompt) | T5 | C-14(b), C-15(a) |
| X-22 | Prompt rủi ro cập nhật: định nghĩa UF/AM theo vai trò (N1–N3, E1–E3), phân tích như thể điều khoản có hiệu lực, quy tắc cận chắc chắn (lương dưới vùng IV; thử việc quá 180 ngày; Điều 25 bốn mức), LV nghi ngờ mà không retrieve được thì LV + INSUFFICIENT, cách nhắc luật kèm tên văn bản; backend: hạ `evidence_status`, kiểm (nhãn, loại căn cứ, vai trò), retry một lần, rồi bản ghi "cần xem xét" | M | N3 | T5 | X-25 (ví dụ neo), C-15(a) |
| X-23 | UI: dòng "Liên quan: Điều X", thẻ "cần xem xét" (nét đứt, không severity), hiển thị số Điều thay `cl_xxxx`, thẻ citation hiện nguyên văn Khoản, thông báo "có thể có rủi ro, chưa đủ căn cứ" | S | N5 | T5 | X-16, X-22 |
| X-24 | Corpus mức Khoản: script parse Điều/Khoản (một lần, dùng lại cho mọi văn bản), nút Điều chỉ chứa tiêu đề và không làm seed BM25, Điều không chia khoản là nút có nội dung; bắt đầu từ phạm vi tối thiểu (S1: ~30 điều BLLĐ trong label_map và lỗi chèn + NĐ 293/2025 vùng IV + 2 nghị định); N3 đưa danh sách điều ưu tiên và nháp `label_map` suy từ cột "Căn cứ" của taxonomy | L | N2 (+N3) | T4–T5 | X-03 |
| X-25 | Xác minh pháp lý (người phụ trách dữ liệu): ca 4 và ca 6 của BRD 3.3 (Điều 35, 49, 105); Điều 25 bốn mức thử việc; mức lương tối thiểu vùng IV hiện hành; hiệu lực các nghị định trong taxonomy; ví dụ neo UF/AM | M | N2 | T4–T5 | — |
| X-26 | `ai_pipeline/eval/alignment.py` (ghép gold với clause pipeline theo span, IoU ≥ 0.5, thừa hưởng nhãn, gold ∈ tập dự đoán) + đánh giá D1 bằng leave-one-group-out theo `similarity_group` kèm khoảng tin cậy (M2, M2b, M7) | M | N2 | T5–T6 | X-04 adapter v06 |
| X-27 | Tập D3 (≥10 cặp mâu thuẫn cài có cạnh Graph + ≥10 cặp đối chứng) + `metrics/contradiction.py` (M10: recall, tỷ lệ báo nhầm, Graph tắt/mở) | M | N2 (dữ liệu) + N1 (metric) | T5–T6 | C-14, X-21 |
| X-28 | `metrics/basis_type.py` (M2b) và `metrics/explanation_quality.py` (M9, cùng 40 mẫu của M3b) | M | N3 | T6–T7 | X-08 |
| X-29 | Lương tối thiểu vùng: provision NĐ 293/2025 trong corpus; quy tắc prompt cận dưới vùng IV; lỗi chèn M5 về lương dùng mức dưới vùng IV; OI-19 (tra vùng đầy đủ theo xã/phường, danh mục trên xaydungchinhsach.chinhphu.vn) chỉ làm nếu dư thời gian | S | N2 + N3 | T5–T6 | X-24, X-25 |

## 4. Kế hoạch từng tuần

### Tuần 1 (12–18/10) — Schema-first, khung dự án (TDD M0)
**Mục tiêu:** mọi mảng có schema mới + mock để làm song song.
- **N1**
  - [x] C-04 (20/10 — chưa có PR): `ai_pipeline/schemas/clause_output_v3.json`; `backend/app/core/enums.py` + `backend/app/clause/taxonomy.py` là nguồn duy nhất; test đối chiếu enum ↔ schema (DEC-20) ở `tests/contract/`. Đã xóa `clause_output_v2.json`. `risk_output_v1.json` thuộc N3 (test đối chiếu enum của nó tự bật khi file xuất hiện)
  - [x] C-03 (20/10 — chưa có PR): đã xóa `ai_pipeline/config/` (`labeling.py`, `taxonomy.py` chuyển sang `clause/taxonomy.py` + `validate_labels`), bỏ `type_scores/tier/review_zone`, bỏ 2 import hỏng `config.risk_routing` (service + `test_pipeline.py`); `clause_extraction_service.py` còn là cầu nối legacy đến C-01
  - [x] Đọc `clause_extraction_service.py` thật, ghi **hiện trạng thực** (20/10 — xem §9, 9 điểm khác/bổ sung so với mô tả C-01)
  - [x] C-19 (phần 1a, 17/10 — chưa có PR): `CLAUSE_TAXONOMY.md`/`DATA_PLAN.md` đã thay bằng con trỏ về BRD 8.2 + số liệu data v06; giữ annotation guideline
  - [x] C-19 (phần 1b, 17/10 — chưa có PR): `README.md`, `CONTRIBUTING.md` (cây thư mục, §3, §7, cảnh báo free tier), `text_extraction_contract.md` (bỏ DOC/`review_zone`/DB, gộp 2 đoạn `extraction_version`, offset code point, masked text) đã khớp SRS/TDD
  - [ ] C-19 (phần 2, T7): `CONTRIBUTING.md` §1–§3 (provider/`.env`, cách chạy test) viết lại khi C-07/C-17 xong
- **N2**
  - [x] Định dạng corpus (`manifest.yaml`, `provisions.jsonl`, `edges.jsonl`, `label_map.yaml`) + 3–5 provision mẫu cho dev (N2 28/10: 5 điểm Điều 21 tại `data/legal_corpus/`, **DRAFT**, chưa duyệt hiệu lực/cho runtime)
  - [x] Bản nháp **danh mục kho luật tầng 1** (theo mục OI-02 trong PROGRESS; trùng mã OI-02 khác nghĩa ở SRS §13) để nhóm chốt ở MS-1 (N2 28/10: shortlist P0/P1 có nguồn chính thức tại `data/legal_corpus/README.md`; **chưa duyệt/chưa đóng cổng MS-1**)
  - [x] Kiểm kê D1 (BRD 8.2: 4 HĐ, 183 clause): còn PII không, đã de-identify chưa; **đối chiếu với data repo v06 (5 HĐ / 234 clause, 183 annotation lịch sử)** và chốt D1 gồm HĐ nào (không tự sửa BRD) — N2 02/11: scope D1 giữ HDLD001–004 (183); HDLD005 là phần bổ sung. Regex canonical 0 email/phone/chuỗi 9–12 số nhưng không chứng minh đã khử PII; review hình/metadata/rights còn mở. BRD không đổi; xem `ai_pipeline/data/docs/archive/reports/D1_DATA_INVENTORY_2026-10-19.md`.
- **N3**
  - [x] X-01: bản đầu **risk taxonomy** theo role, bảng severity theo (nhãn, `basis_type`, role) với `basis_type` = LEGAL_VIOLATION/UNFAVORABLE/AMBIGUOUS; nháp severity rubric
  - [x] `risk_output_v2.json` (chỉ cho câu trả lời LLM, thay tên `risk_output_v1`); `backend/app/risk/taxonomy.py` là nguồn duy nhất của nhãn + bảng severity; `risk_assembler.py` ghép ra `risk_merged_v1`; test đối chiếu doc ↔ code ↔ schema (xem `changes.md`)
  - [x] (cùng N4, chưa có PR/commit) `final_result_v1.json` và fixture tiếng Việt đã de-identify; test contract đối chiếu enum, span partition và citation.
  - [x] pre C-09: Spike PII: danh sách pattern regex tiếng Việt (email, SĐT, CCCD/CMND, TK ngân hàng, ngày sinh, tên, địa chỉ, pháp nhân); `backend/privacy/pii_DRAFT.py` + `tests/unit/test_pii_draft.py`. Chưa đo precision/recall trên D1
- **N4**
  - [x] C-17 (chưa có PR/commit): pytest offline cho schema/API/config + workflow Python 3.12; không dựng INV-01…12 giả khi stage chưa có.
  - [x] Package `backend/app/{domain,session,document,privacy,ai,legal,result,ops}` và `core/config.py`: settings đọc env lúc gọi, demo/eval fail-fast; chưa load corpus/DB.
  - [x] Mock API 6 operation cho N5: dev-only, fixture thay phân tích thật; không thực thi production admission/rate/quota/lease, pipeline C-05/C-06 còn chờ T2.
  - [x] C-20: `pyproject.toml` là nguồn deps UTF-8, Python 3.12; bỏ `backend/requirements.txt`.
- **N5**
  - [x] Chọn framework (đề xuất React + TS + Vite), dựng skeleton `frontend/`; `api/types` theo mock
  - [x] `lib/offset.ts` (code point → UTF-16) + test non-BMP (INV-12)
  - [x] X-07: soạn disclaimer + data notice từ BRD Phụ lục A
  - [x] Trang Upload (role bắt buộc) chạy với mock

**Cổng T1:** schema mới merge; mock chạy; không ai code trên schema cũ; `pytest` xanh; OI-04 (phân công) chốt.

### Tuần 2 (19–25/10) — MS-1: đóng băng taxonomy; bắt đầu phiên/API + tiền xử lý (TDD M1, M2)
- **N1**
  - [x] C-02 (25/10): `backend/app/clause/structure_parser.py` (5 pattern, level/parent bằng stack, list yếu cần ≥2 mục + đánh số liên tiếp, loại số tiền `2.000.000`), **đã xóa** `utils/text_processing.py` (`document_router`, `CLAUSE_PATTERN`); fixture `tests/fixtures/segmentation/{nested_article_subclauses,paragraph_fallback,lists_false_positives}.txt`
  - [x] C-01 (a) (25/10): `backend/app/clause/segmenter.py` `segment()` v1 (`rules_v1.1`) — partition không chồng lấn, fallback paragraph (<40 ký tự gộp neighbor), clause >4000 ký tự giữ + warning, `TOO_MANY_CLAUSES` (>150), tự kiểm INV-02/03 trước khi trả; test `tests/unit/test_{structure_parser,segmenter}.py` + `tests/integration/test_segmenter_real_contracts.py` (6 hợp đồng thật). `classify()` (C-01 b) còn ở T3–T4; `clause_extraction_service.py` vẫn là cầu nối legacy
  - [x] **Freeze** clause taxonomy + chính sách đa nhãn (OI-10) — **xong một phần, chờ N2/N3**: phần **kỹ thuật đã khóa** (`docs/CLAUSE_TAXONOMY_FREEZE.md` §1 + `tests/unit/test_clause_taxonomy_freeze.py`, fingerprint). Phần **chính sách** (đa nhãn §2; bảo mật/không cạnh tranh, giải quyết tranh chấp, bồi thường NLĐ §3) là **[Đề xuất N1] — chờ N2/N3 sign-off** (§4 của file đó); chưa xác nhận nên **chưa đổi** `LABEL_DEFINITIONS`
- **N2**
  - [ ] **Freeze** annotation guideline; **chốt danh mục tầng 1** (MS-1) (trễ: chốt cùng đợt X-25; guideline gồm định nghĩa UF/AM theo vai trò, BRD 3.2)
  - [x] X-03: nhập provisions tầng 1 đợt 1 + `label_map` v0 — N2 02/11: corpus DRAFT có 16 provision candidate, 16 citation ID duy nhất và 5 label mappings; mọi dòng vẫn chờ đối chiếu chữ/hiệu lực pháp lý, xem `data/legal_corpus/README.md` và review queue ở repo dữ liệu. Đây là hoàn tất nhập batch nháp, không phải duyệt corpus.
  - [x] X-10 kickoff: bắt đầu tìm/triage nguồn T1 và lập quy trình intake + de-identify — N2 02/11: manifest repo dữ liệu có 22 ứng viên; đã có hướng dẫn cổng quyền sử dụng/ẩn danh và hàng chờ xin quyền; test intake gate 9/9 pass. **Chỉ hoàn thành mốc khởi động**: 0/22 ứng viên đủ điều kiện T1, yêu cầu liên hệ chưa gửi, chưa có quyền dùng hay bản dẫn xuất ẩn danh được nghiệm thu; mục tiêu X-10 ≥10 hợp đồng T1 vẫn mở.
- **N3**
  - [x] **Freeze** risk taxonomy + severity rubric (MS-1) — cả nhóm review
  - [x] C-09 (a): `pii_types`, `mask_value`, `detector` regex (email, SĐT, CCCD, TK NH)
  - [x] **INV-01** test (tests/unit/test_inv01_mask_length.py)
- **N4**
  - [x] C-05: `InMemorySessionStore`, `ProcessingLease`, state machine; barrier hai lần acquire đồng thời, Create bị chiếm lease, Retry bị chiếm và End vs callback.
  - [x] C-06 (a): gate role → rate → quota → lease, sáu route lifecycle và cap streaming; chỉ runner fixture dev, chưa phân tích hợp đồng thật.
  - [x] `ops/metadata_db.py`: SQLite metadata-only cho quota/rate/tombstone và schema run_log.
  - [ ] X-11: ghi sai khác docs vào nhật ký §9, không sửa BRD/SRS/SDD/TDD đã freeze; O-09 cần đối chiếu, O-11/BR-14 đề xuất errata, DEC-17 chờ nhóm duyệt.
- **N5**
  - [ ] `usePolling` (500 ms → 1,5 s → 2,5 s), catalog thông báo lỗi (TDD Phụ lục E)
  - [ ] Trang Progress + Result (layout) trên mock `final_result_v1`; highlight dùng offset map

**Cổng MS-1 (25/10):** 4 artifact (clause taxonomy, risk taxonomy, severity rubric, annotation guideline) đã đóng băng; risk taxonomy có người phụ trách; danh mục kho luật tầng 1 chốt.

### Tuần 3 (26/10–1/11) — Tiền xử lý cục bộ chạy được trên D1
- **N1**
  - [x] C-01 (b) (01/11 — chưa có PR): `segment()` không đổi logic (đã đủ từ W2); thêm `tests/unit/test_segmenter_pii_boundary.py` (fuzz 400 văn bản có PII, seed cố định: INV-01/02/03 + ranh giới không trong placeholder, non-BMP). **Lưu ý:** 6 hợp đồng D1 đã de-identify ⇒ `mask()` trả 0 span, nên ranh giới PII chỉ được kiểm bằng văn bản tổng hợp. `boundary_guard` vẫn re-export từ `privacy/masker.py` (chờ N3 đồng ý chuyển)
  - [x] C-07 (01/11 — chưa có PR): `ai/provider.py` (`LLMProvider`, `CallLedger`, `InMemoryLedger`, `call_with_retry`: retry ≤1 gộp mọi loại lỗi, 429 backoff+jitter, 400/401/403 không retry, before_call/after_call cho MỌI request kể cả retry, message lỗi không chứa prompt/body), `ai/gemini_client.py` (key qua header `x-goog-api-key`, `responseSchema`, temperature từ cấu hình, không có model mặc định ngầm), `ai/dev_local_client.py` (chặn ngoài `APP_ENV=dev`), `ai/factory.py`; `domain/errors.py` thêm `AiTimeout/AiProviderError/AiOutputInvalid/StageCancelled`. **Chưa gọi Gemini thật** (không có key/mạng): phần dịch JSON Schema → `responseSchema` cần xác nhận bằng job `llm-live`. Chưa xóa `ai_pipeline/services/llm_clients.py` + `clause_extraction_service.py` (legacy, còn `tests/llm/test_llm_live.py` dùng) — xóa khi `classify()` chạy được ở T4
  - [x] `ai/prompts/clause_v1.py` (sinh từ `LABEL_DEFINITIONS`; `prompt_pin()` đổi khi prompt/định nghĩa đổi) + `ai/clause_adapter.py` khung (`classify_clauses`: lô `CLAUSE_BATCH_SIZE`, song song ≤`LLM_PARALLELISM`, cancel trước mỗi lô, validate đúng-1-lần/1–3 nhãn/field lạ ⇒ INV-05, INV-04 test chặn payload). Test: `tests/unit/test_{llm_provider,gemini_client,clause_prompt,clause_adapter}.py`, `tests/contract/test_clause_adapter_output.py`. **Còn lại cho T4:** nối `Settings`/orchestrator, chạy D1, đo M1/M7, bỏ legacy
- **N2**
  - [x] C-12 (a): `corpus_loader`, `corpus_validator` (overlap hiệu lực, endpoint cạnh, PARENT_OF acyclic) + fixture `valid/`, `invalid_overlap/`, `invalid_edge/` (N2 28/10: offline loader/checksum/approval gate và test; chưa tích hợp production)
  - [x] X-03: provisions tầng 1 đủ để baseline chạy ở chế độ offline/DRAFT — N2 02/11: `test_draft_corpus_retriever_is_blocked_by_default` nạp corpus thật với `allow_draft=True` và xác nhận BaselineRetriever trả candidate; mặc định vẫn chặn. Đây là smoke test cấu trúc, không phải chạy benchmark, Recall@5 hay chứng minh mức bao phủ luật.
  - [ ] X-04: bắt đầu gold segmentation D1 (sửa tay ranh giới) để đo M1 — dataset v06 là gold nhãn clause (1 dòng/1 nhãn, bỏ heading, 9 dòng `CONTEXT` `span=null`), **không** dùng làm gold M1; viết adapter v06 → `clause.json` (TDD §18.3) và policy `CONTEXT` trước khi tính F1; quy đổi sang đầu ra pipeline theo BRD 8.3 (X-26)
- **N3**
  - [x] C-09 (b) (01/11 — chưa có PR): heuristic tên / pháp nhân / địa chỉ / ngày sinh, preserve-list, resolve overlap; sửa MST bị gán PHONE, tên bị cắt tại `Quốc/Năm/Điện…`, thêm SĐT bàn 02x; `pii_draft_0.3`
  - [x] Phối hợp N1 tích hợp `boundary_guard` ↔ `pii_spans`; fixture `privacy/` (N1 có `test_segmenter_pii_boundary`; N3 thêm `case_005`–`case_008` + `test_pii_fixtures_gold.py`)
  - [ ] Gold privacy: dùng Gold D1/T1 đã khóa cho phép đo cơ sở; P1 (X-18) là phép thử mở rộng khi có gói Gold riêng. T2 privacy hiện chỉ có tham chiếu suy ra, phải ghi rõ giới hạn này.
- **N4**
  - [x] C-08 (a) (31/10 — commit 1 `feat: implement PDF extraction and canonical quality gates (C-08a)`): PyMuPDF, 2 cột, header/footer ≥60% trang, bảng `|`, `canonicalizer`, `quality` (fixture legacy TCVN3 fail); `extraction_v1` schema, smoke PDF tiếng Việt cục bộ; **chưa chạy D1** (N2 chưa xác nhận bộ D1), chưa nối API/orchestrator.
  - [x] C-10 (31/10 — commit 2 `feat: add local labor-contract scope precheck (C-10)`): `scope_rules_v1` chấm điểm theo TDD §9 trên bản sao canonical, fixture dương/âm và biên tiêu đề; smoke PDF tiếng Việt thật sau C-08(a). **Ngưỡng OI-03 chỉ tạm thời, chờ đo D1**; đã ghép vào luồng kiểm chứng cục bộ ở commit 4, chưa nối HTTP/Orchestrator.
  - [x] C-11 (31/10 — commit 3 `refactor: remove standalone explanation AI adapter (C-11)`): xóa adapter rỗng `integrations/explanation_ai.py`; cập nhật `backend_architecture.md` về đúng 2 lần gọi LLM và hiện trạng dev mock; không đụng `PROCESSING` hoặc adapter N1/N3.
  - [x] Commit 4 `f698928` (`feat: compose local PDF validation pipeline (N4 W3)`): `session/local_validation.py` ghép PDF → canonical → scope → mask toàn văn → segment chạy cục bộ qua threadpool; kiểm chứng PDF tiếng Việt thật, từ chối ngoài phạm vi và vượt giới hạn clause; INV-01/02/03 trên fixture PDF. Không tạo kết quả mẫu/ghi nội dung ra đĩa từ runner. **Chưa chạy D1** và chưa nối HTTP `VALIDATING` vào runner.
  - [ ] Nối HTTP `VALIDATING` vào pipeline thật khi có stage tiếp theo: upload giữ đầu vào trong RAM, quản lý lease/cancel/retry/REJECTED; dev sample tách biệt, không trả fixture cho PDF thật. Chưa thể đánh dấu hoàn tất khi Clause Graph/PROCESSING chưa có.
- **N5**
  - [ ] Result page highlight thật trên mock; nút Retry/End; đủ nhánh REJECTED/FAILED/EXPIRED
  - [ ] C-21 (a): `build_report_model` trên mock

**Cổng T3:** PDF → canonical → mask → segment chạy end-to-end cục bộ trên D1 (chưa gọi LLM); INV-01/02/03 xanh.

### Tuần 4 (2–8/11) — MS-2: tới Clause Classification trên D1
- **N1**
  - [x] `classify_clauses` đầy đủ (W4, 07/11 — chưa có PR): batch (20), song song (2), kiểm cancel **trước và sau** mỗi lô (callback muộn sau End bị bỏ), validate (mỗi ID đúng 1 lần, 1–3 nhãn), retry ≤1 → `AI_OUTPUT_INVALID` (đúng 2 call tối đa); **INV-05** (field lạ bị từ chối); chạy được với `Settings` thật; thêm `masked_items_from_segmentation` (cầu segmentation → classify, chỉ masked text, INV-04)
  - [x] Chạy trên D1 (Gemini not-paid, dữ liệu đã che); đo sơ bộ M1, M7 (07/11/2026): chạy gemini-3.5-flash-lite trên HDLD001–004 (do gemini-2.5-flash bị vượt quá quota); 12 calls/0 errors, 22.411 in / 7.518 out tokens; M7 preliminary macro-F1 = 0.4974 trên 12 nhãn (111/174 aligned spans); M1 proxy F1 = 0.5323 (tham chiếu span nhãn, không phải gold segmentation).
  - [x] C-14 (a) (W4, 07/11 — chưa có PR): `clause/graph_builder.py` `build_clause_graph` NEXT + PARENT_OF (cha trước con, level cha < con, không chu trình/self-loop/đa cha → `PipelineInternalError`; `ORPHAN_NESTED` là diagnostic); `tests/unit/test_graph_builder.py`, `test_inv08_graph_no_text.py` (**INV-08**: duyệt object + serialize, không text/offset/số điều). Chữ ký: `build_clause_graph(clauses, masked_text=None)` — bỏ tham số `structure` vì đã nằm trong `SegmentedClause.structure` (SKELETON §5.6 đã sửa). REFERS_TO để W5 (C-14 b)
  - [x] X-20 (phần N1) (W4, 07/11): `boundary_guard` + `adjust_boundary` chuyển về `clause/segmenter.py`; `privacy/masker.py` re-export (test của N3 không đổi); `tests/unit/test_boundary_guard.py` dùng span viết tay
- **N2**
  - [x] C-12 (b): `BaselineRetriever` (label_map + BM25 `0.70/0.30`, hiệu lực, dedupe, seed/pool) — N2 28/10: module độc lập có unit test, từ chối DRAFT mặc định; **chưa có tích hợp startup/runtime, chưa đo M8 trên gold D1/D2**
  - [x] C-13 (a): Data Graph cấu trúc (PARENT_OF tự sinh) + REFERS_TO/GUIDES verified đợt 1 — N2 02/11: `DataGraph` in-memory + PARENT_OF tự sinh; thêm cạnh thật `BLLD2019:art14:cl1` → `BLLD2019:art14:cl2` (`REFERS_TO`) sau khi đối chiếu trực quan trang 7 PDF chính thức 18/VBHN-VPQH (SHA-256 ghi trong `data/legal_corpus/README.md`); unit tests corpus/graph 50 pass. **Chỉ đóng batch kỹ thuật đầu tiên**: cạnh và corpus vẫn DRAFT/chờ reviewer pháp lý độc lập; chưa xác nhận hiệu lực hiện tại hoặc đủ điều kiện cite/đánh giá hợp đồng.
    - [x] N2 28/10: `DataGraph` in-memory + PARENT_OF từ `parent_path`, MANUAL edge index, duyệt hai chiều có lọc ngày hiệu lực; fixture và unit test. Tại checkpoint này chưa có cạnh thật; được bổ sung và source-check ở ghi chú N2 02/11 phía trên.
  - [ ] Kho luật tầng 1 bản đầu theo đơn vị Khoản (X-24, bắt đầu từ phạm vi tối thiểu); gold clause labels D1
  - [ ] X-25: xác minh pháp lý (ca 4, ca 6 BRD 3.3; Điều 25; vùng IV; hiệu lực nghị định); bàn giao intake X-10 cho N5 (22 ứng viên, 0 xin quyền xong)
- **N3**
  - [x] **Báo cáo số đo PII đầu tiên** (01/11): `docs/PII_MEASUREMENT_2026-11-01.md`, sinh bởi `ai_pipeline/eval/eval_pii.py`. D1 là biểu mẫu trống nên chỉ đo được trên fixture tổng hợp; OI-12 **chưa chốt**, chờ gold privacy D1 (N2) hoặc hợp đồng thật
  - [x] Thiết kế prompt `risk_v1` + khung `risk_adapter` với provider mock (01/11): `ai/prompts/risk_v1.py`, `ai/risk_adapter.py`; test `test_risk_prompt`, `test_risk_adapter`, `contract/test_risk_adapter_output`
  - [ ] X-12: áp bộ 5 patch tài liệu (hạn 05/11), cả nhóm review; chỉ định chủ biên từng tài liệu
  - [ ] X-15: PR taxonomy một lần (đổi nhãn, đổi cột, rà severity, hằng fingerprint) rồi freeze lại; X-16 (`risk_output_v2`: `related_clause_ids`)
  - [ ] X-17 + X-18: bốn loại PII mới và bộ sinh gold P1; đưa N2 danh sách điều ưu tiên + nháp `label_map` cho X-24
- **N4**
  - [ ] C-08 (b): DOCX extractor (numbering, tracked changes accepted-state, textbox); phạm vi numbering (OI-11)
  - [ ] C-16 (a): `RunLogWriter`, `DailyQuota.before_call/after_call` (tăng nguyên tử **trước** call), `EvalCostLedger` khung
  - [ ] X-05 (a): bộ đo benchmark D1 (p50/p90 từng stage)
  - [ ] **Họp chốt cấu hình mở:** SRS OI-03, 05, 09–12
  - [ ] X-13: khóa chữ ký hàm + schema (05/11); X-16 (`final_result_v1`: `clause`, `related_clause_ids`)
  - [ ] X-20 (phần N4): fixture mock cạnh `session/mock.py`; `_ALLOWED` thêm VALIDATING→EXPIRED và PROCESSING→EXPIRED
- **N5**
  - [ ] Ghép frontend với backend thật tới trạng thái PROCESSING; polling ≤2 s hiển thị VALIDATING/PROCESSING
  - [ ] Catalog lỗi đầy đủ theo `error_code`
  - [ ] X-14: vẽ lại ảnh SRS/SDD từ Mermaid (ARCHITECTURE §2); X-10: nhận bàn giao thu và de-identify hợp đồng T1 từ N2

**Cổng MS-2 (08/11):** pipeline tới Clause Classification chạy trên D1; kho luật tầng 1 bản đầu + Data Graph cấu trúc; PII có số đo đầu; cấu hình mở đã chốt; bộ 5 patch tài liệu đã áp (X-12) và chữ ký hàm + schema đã khóa (X-13, dự kiến 05/11).

### Tuần 5 (9–15/11) — Retrieval + Risk + Clause Graph (TDD M4, M5)
- **N1**
  - [ ] C-14 (b): `REFERS_TO` (regex) **loại trừ dẫn chiếu pháp luật**; `resolve_context` (≤3 clause, ≤6000 code point); `ContextResolutionTrace`; fixture `refers_contract`, `excludes_legal_reference`; X-21: clause JOB_INFO và CONTRACT_TERM_TYPE làm context chung
  - [ ] Tuning classification trên D1/D2 (version config)
- **N2**
  - [x] C-13 (b) (01/11, fixture/offline): `DataGraph.expand` + `get_candidates` (seed-first, merge, **cùng `final_k`**; lỗi runtime → fallback + `graph_fallback`); 25 graph test cases cover ranking/direction, caps, dedupe, date gates, graph-off/fallback, invalid caps and budget alignment. Full suite green (9 private-data skips); Ruff clean. **Not production-wired; corpus remains DRAFT; no Recall@5 claim.**
  - [ ] Tuning `label_map`/trọng số trên D1/D2
  - [ ] X-26: alignment + leave-one-group-out cho D1; X-27 (dữ liệu D3: cặp mâu thuẫn cài + đối chứng); X-29 (provision NĐ 293/2025)
  - [ ] X-04: D2 lỗi chèn (dev, tách quy định khỏi T2); gold seg T1 cho hợp đồng đã thu
- **N3**
  - [ ] C-15 (a): `risk_adapter` đầy đủ (candidate catalog dedupe, related context, structured output, batch 6); `detect_advice` (theo cụm, không match "nên" đơn), `detect_unsupported_reference`, `sanitize_explanation`; X-22: prompt cập nhật (UF/AM theo vai trò, cận chắc chắn, LV nghi ngờ → INSUFFICIENT, cách nhắc luật, `related_clause_ids`)
  - [ ] `citation_validator` (INV-06); `risk_assembler` (dựng `risk_basis`, tra severity) (INV-07); hạ `evidence_status` về INSUFFICIENT khi hết citation hợp lệ; kiểm (nhãn, loại căn cứ, vai trò), retry một lần, rồi bản ghi "cần xem xét"
- **N4**
  - [ ] Nối thật `PROCESSING` trong orchestrator; **retry/resume** (`failed_stage` → VALIDATING/PROCESSING; resume chỉ ở giai đoạn AI, so khớp version pin thay cho fingerprint; VALIDATING chạy lại từ EXTRACTION; trễ thì cắt item 2); cancel; test End vs callback muộn
  - [ ] X-19: `backend/app/pipeline.py` `analyze()` (orchestrator và harness cùng gọi)
  - [ ] `cleanup` + tombstone 24h; route `export`; **INV-09/10**
  - [ ] C-16 (b): `SlidingWindowLimiter` (HMAC IP)
- **N5**
  - [ ] C-21 (b): `export_docx` đủ quote, risk + basis, severity/"chưa đủ căn cứ", explanation, citation, disclaimer, **data notice**
  - [ ] UI: `INSUFFICIENT_EVIDENCE` (không badge severity), không risk ("Không phát hiện rủi ro trong phạm vi phân tích")
  - [ ] X-23: dòng "Liên quan: Điều X", thẻ "cần xem xét", số Điều thay `cl_xxxx`, thẻ citation hiện nguyên văn Khoản

**Cổng T5:** test tích hợp toàn pipeline với LLM mock xanh; INV-01…11 có test; DOCX xuất được; `related_clause_ids` hiển thị; thẻ "cần xem xét" hiện đúng.

### Tuần 6 (16–22/11) — Chạy thật cả hai vai trò, đo chi phí/hiệu năng
- **N1**
  - [ ] Pipeline thật (Gemini paid) trên D1 cho cả 2 vai trò; sửa lỗi segmentation/classification
  - [ ] `metrics/segmentation.py` (M1), `metrics/clause_classification.py` (M7); `metrics/contradiction.py` (M10, X-27)
- **N2**
  - [x] `runner.py` + `load_dataset`; `metrics/citation_validity.py` (M3a), `quote_span.py` (M4), `injected_recall.py` (M5), `retrieval.py` (M8 on/off, predicted labels primary) — N2 02/11: offline/fixture scope complete; 32 focused tests pass. No claim that C-18 as a whole is complete: production adapter, M1/M2/M6/M7, approved gold and D1/T2 runs remain open.
    - [x] N2 01/11: strict JSON dataset loader (duplicate-key/path-escape checks); pure M3a/M4/M5 metrics; paired M8 metric + callback runner dùng cùng masked text/predicted labels/date/final_k cho graph off/on. Fixture/offline only; no approved corpus/gold or D1/T2 evaluation.
  - [ ] X-04: bắt đầu **T2** — chèn lỗi (mục tiêu ≥30, mỗi role ≥10; lỗi lương tối thiểu dùng mức dưới vùng IV), 2 người xác minh mỗi lỗi
- **N3**
  - [ ] Chạy M5/M8 trên D2 (dev) để tune lint + prompt (version prompt)
  - [ ] `metrics/risk_classification.py` (M2); X-08 khung judge (M6); X-28 (M2b, M9)
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
  - [ ] Xóa mã legacy (`ai_pipeline/services/`, `ai_pipeline/test_pipeline.py`) và các sys.path hack còn lại (`tests/llm/test_llm_live.py`, `scripts/smoke_llm_pipeline.py`)
  - [ ] Bug bash segmentation/classification trên D1/D2
- **N2**
  - [ ] Dry-run `runner` trên D1/D2 (không đụng T1/T2 để tuning)
  - [ ] Hoàn tất lỗi chèn T2 + gold; ghim `corpus_version`, `data_graph_version`
- **N3**
  - [ ] X-08: hiệu chuẩn judge (M6 ≥80% & κ≥0.6) trên mẫu 40; BL-1 (nếu chưa cắt)
  - [ ] Ghim `risk_prompt_version`, `severity_rubric_version`
- **N4**
  - [ ] X-06 (chỉ nếu nhóm chọn hosting; hiện chạy localhost): hosting + HTTPS + **đúng 1 worker** (smoke fail nếu >1) + chốt biến môi trường demo
  - [ ] Tối ưu hiệu năng khi p90 trên hợp đồng 15 trang của D1 vượt 100s theo thang TDD §17.6: song song 2→4; giảm context rồi batch 6→8 (mỗi bước chạy lại M2, nhận nếu F1 giảm ≤2 điểm); hạ trần clause hoặc xin nới ngưỡng; không đổi invariant
  - [ ] Test fail-fast khi thiếu `GEMINI_MODEL_ID`/quota/reserve ở demo
- **N5**
  - [ ] Hoàn thiện UI, thông điệp lỗi, kịch bản demo; export DOCX kiểm lần cuối
  - [ ] (nếu còn thời gian) PDF export — **cut item 4**, cần chủ BRD duyệt nếu bỏ

**Cổng T7:** đã triển khai chạy được; harness chạy đủ M1–M10 (M10 trên D3) trên D1/D2; checklist TDD Phụ lục D còn ≤ vài mục.

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

- T9 → **MS-4 (13/12):** chạy T1 (M1, M2, M2b, M3a, M3b, M4, M6, M7, M9, BL-1) + T2 (M5, M8; graph on/off cùng `final_k`) + D3 (M10); ngân sách đánh giá $15 qua `eval_cost_ledger`.
- T10 → **MS-5 (20/12):** báo cáo (nêu giới hạn: gold không có luật sư, M5 là recall trên rủi ro có căn cứ rõ, **không nêu mức phạt** do BRD OI-08) + bảo vệ.

## 6. Quyết định cần người chốt (đừng tự "sửa ngầm")

| Việc | Hạn | Ai |
|---|---|---|
| OI-04 phân công mảng chưa có chủ (xác nhận §2) | T1 | cả nhóm |
| OI-01 risk taxonomy có chủ + bản đầu | T1–T2 (MS-1) | N3 |
| OI-10 chính sách đa nhãn (1–3 nhãn, ưu tiên 1) — freeze cùng guideline; kèm quy tắc quy đổi dataset single-label ↔ prediction đa nhãn | MS-1 | N1 + N2 — **N1 đã đề xuất** ở `docs/CLAUSE_TAXONOMY_FREEZE.md` §2, chờ N2 xác nhận |
| D1/T1 từng lệch vì data repo v06 có HDLD005: đã chốt D1 = HDLD001–004 (183) và HDLD005 thuộc T1; BRD 0.6 §8.2 được đồng bộ ngày 06/11 | Đã xử lý | Chủ dự án + N2 |
| Test split đang công khai trong repo, mới provisional; thiếu WORKING_TIME (test) / TERMINATION (dev) — khóa split, giữ kín T1 | trước MS-4 | N2 |
| Topic bảo mật/không cạnh tranh, giải quyết tranh chấp chưa có nhãn data v0.3 chốt — đưa vào annotation guideline | MS-1 | N1 + N2 — **N1 đã đề xuất** ở `docs/CLAUSE_TAXONOMY_FREEZE.md` §3 (cùng bồi thường NLĐ; khớp `POST_EMPLOYMENT_RESTRICTION` của N3), chờ N2/N3 |
| BRD **BR-14** ghi "cập nhật kho luật đòi hỏi sửa mã nguồn" mâu thuẫn FR-24/BRD §6 → có thể thiếu chữ "không" | T2 | chủ BRD |
| SRS **DEC-17** (bỏ `type_scores`, tier, `review_zone`) cột người chốt ghi "Không duyệt" trong khi TDD vẫn dùng (BRD OI-18) | T2 | chủ SRS |
| SRS OI-03 (ngưỡng scope precheck), OI-05 (quota/reserve), OI-11 (đánh số DOCX), OI-12 (local NER) | MS-2 | cả nhóm |
| Bộ 5 patch tài liệu (X-12): chỉ định chủ biên từng tài liệu; ghi tên người chốt cho DEC-17 (SRS 1.5 đang ghi "Cả nhóm, chờ ghi tên người chốt") | 05/11 | cả nhóm |
| Ngày khóa chữ ký hàm + schema (X-13) và re-freeze taxonomy sau X-15 | 05/11 | N4 + N3 |
| Hosting: hiện localhost; nếu sau này chọn nền tảng thì bàn riêng (kiểm HTTPS, giới hạn upload, đĩa bền cho quota, một worker không ngủ đông) | khi cần | cả nhóm |
| Chia lại tải (O-06): X-10 sang N5; X-24 bắt đầu từ phạm vi tối thiểu; N3 hỗ trợ danh sách điều ưu tiên | T4 | cả nhóm |
| Cách hiện thực hard byte cap khi upload; ý nghĩa `progress.total_units`; mã HTTP của retry (`SKELETON.md` §13) | T2 | N4 |
| BRD OI-03 pháp lý dữ liệu cá nhân gửi ra nước ngoài (chưa xác nhận) | trước demo | cả nhóm |

## 7. Thứ tự cắt khi trễ (BRD §9.5 — cắt từ trên xuống, không nhảy bước)

1. BL-1 (so với LLM thông dụng)
2. Stage resume (chỉ giai đoạn AI) → retry chạy lại giai đoạn PROCESSING từ đầu, vẫn giữ giới hạn 2 lần
3. LLM hỗ trợ tách điều khoản → chỉ luật + fallback paragraph (hiện đã là mặc định)
4. Export PDF → chỉ DOCX (**cần chủ BRD duyệt**, vì BR-02 yêu cầu cả hai)
5. Graph → chỉ giữ cạnh cấu trúc, bỏ `REFERS_TO`/`GUIDES` (**cần chủ BRD + giảng viên duyệt**; Data Graph và Clause Graph vẫn phải có — BR-17, BR-18)

## 8. Đường găng và rủi ro tiến độ

| Chuỗi phụ thuộc | Rủi ro | Biện pháp |
|---|---|---|
| risk taxonomy (MS-1) → `risk_adapter` (C-15) → `risk_assembler` | OI-01 chưa có chủ ⇒ N3 bị chặn từ T4 | Chốt chủ ở T1, bản đầu ở T1–T2 |
| danh mục tầng 1 → corpus → baseline → Data Graph → M8 | Kho luật sai/thiếu, không có luật sư | Closed corpus + `INSUFFICIENT_EVIDENCE`, edges chỉ load khi đã verified |
| C-08 (L) extraction → segmentation → toàn bộ pipeline | N4 nặng nhất | Mock/fixture canonical để N1/N3 không phải chờ; C-07 đã chuyển cho N1 |
| C-09 (L) PII → `boundary_guard` → INV-03 | PII recall không đạt BRD 7.3 | Đo sớm trên D1 (T4); local NER chỉ thêm nếu D1 không đạt (OI-12) |
| X-10 tiếp nhận T1 theo cổng tương đương | 10/10 tài liệu đã được nhóm phê duyệt theo cấu trúc 4 hạn chế + 5 mẫu + 1 tổng hợp; quyền phân phối và chấp thuận của chủ thể không suy ra từ hash | Giữ dữ liệu hạn chế cục bộ; báo riêng unique 8, T1 real 9 và composite 10; xem BRD 0.6 §8.2 |
| X-05 benchmark → quota/reserve (OI-05) | Số đo đến muộn ⇒ không khóa được cấu hình demo | Benchmark chạy từ T4, chốt ở T6 |
| Frontend chưa có đối chiếu (X-02) | Phạm vi chưa ước lượng | N5 làm trên mock từ T1; checkpoint với N4 mỗi tuần |

## 9. Nhật ký (ghi khi làm xong / khi kế hoạch đổi)

| Ngày | Người | Việc / PR / commit | Ghi chú (sai khác so với mô tả Phụ lục C, đổi kế hoạch…) |
|---|---|---|---|
| 2026-10-13 | — | Tạo `AI_CONTEXT.md`, `ARCHITECTURE.md`, `split_doc.py`, `SKELETON.md`, `PROGRESS.md` | Snapshot codebase chưa có frontend; Phụ lục C chưa đối chiếu mã thật |
| 2026-10-20 | N1 | C-04, C-03 + đối chiếu mã thật `clause_extraction_service.py` (T1, làm trễ so với hạn 18/10 — chưa có PR/commit) | **Đã làm:** thêm `backend/app/core/enums.py`, `backend/app/clause/taxonomy.py` (`DATA_TAXONOMY_VERSION=clause_taxonomy_v03`, `TAXONOMY_VERSION=v04`, `validate_labels`), `ai_pipeline/schemas/clause_output_v3.json` (theo TDD Phụ lục A.1), `mock_clause_service.get_mock_clause_output()` theo v3, test `tests/unit/test_clause_taxonomy.py`, `tests/contract/{test_schema_enums,test_clause_output_v3}.py` (52 passed / 1 skipped; đã thử cố ý làm lệch taxonomy → test fail đúng). Xóa `ai_pipeline/config/`, `clause_output_v2.json`. Sửa đường dẫn trong `tests/test_data_lead_review.py`, `scripts/audit_data_lead.py`; thêm `pythonpath=[".","backend"]` + `jsonschema` dev dep vào `pyproject.toml` (**N4/C-17, C-20 chú ý để tránh xung đột khi merge**). Docs: `CONTRIBUTING.md`, `docs/CLAUSE_TAXONOMY.md`, `AI_CONTEXT.md` §9, `SKELETON.md` §2 (ghi chú) |
| 2026-10-20 | N1 | **Hiện trạng thực `clause_extraction_service.py` (đối chiếu C-01)** | (1) Đúng mô tả: 1 lần gọi LLM với **toàn bộ** `raw_text` chưa che PII, không batch; `_locate_span` dùng `str.find`, nhánh "chuẩn hóa khoảng trắng" **trả `None` cả hai trường hợp** (mã chết). (2) **`config/risk_routing.py` không tồn tại trong repo** (không chỉ "import hỏng") ⇒ service và `test_pipeline.py` không import được từ đầu; "2 import hỏng" = 2 file đó. (3) Service **không gọi `document_router`** — chỉ `test_pipeline.py` gọi; nghĩa là không có "Pipeline A regex", C-02 bỏ router không ảnh hưởng service. (4) LLM trả cả `clause_type` + `type_scores`; service **bỏ `clause_type` của LLM**, tính lại bằng `resolve_multi_labels` (ngưỡng 0.60, tối đa 3) — `type_scores` là nguồn nhãn thật. (5) Nhãn lạ bị lọc im lặng, nhãn thiếu = 0.0 (không có `AI_OUTPUT_INVALID`); `clause_id` dạng `clause_N` (không phải `cl_0001`). (6) `span` có thể `null` (khi LLM diễn giải) ⇒ vi phạm INV-02/03; schema v2 lại bắt `span` là object ⇒ output service **chưa từng validate được** với schema v2 (không test nào dùng schema). (7) Output thiếu `schema_version`, `taxonomy_version`, `multi_label_rule_version` mà schema v2 yêu cầu. (8) Import kiểu `from config...`/`from services...` ⇒ chỉ chạy khi cwd=`ai_pipeline/`, không import được dạng package. (9) `mock_clause_service.py` mang `tier/review_zone/review_reason` và không ai import. **Bổ sung cho C-07 (`llm_clients.py`):** key trong query string, model mặc định ngầm `gemini-2.0-flash`, timeout 60s/120s, `temperature=0.1` (TDD: 0.0), chỉ `responseMimeType` (không `response_schema`), không retry — khớp mô tả C-07. **Cầu nối tạm:** service chỉ đổi phần nhãn (prompt xin `clause_labels`, kiểm bằng `validate_labels`, sai ⇒ `LLMClientError`, `clause_id=cl_NNNN`); vẫn còn `_locate_span`/`contract_id` đến khi C-01 thay |
| 2026-10-20 | N1 | Nhận `data.zip` (release `v06-rc1`), đặt vào `ai_pipeline/data/`, đối chiếu với code/tài liệu (chưa có PR) | 30/30 hash manifest khớp; validator 0 lỗi; 28 pass + 1 skip (test data repo); `tests/test_data_lead_review.py` pass đủ (trước đó 5 lỗi vì submodule rỗng); 12 nhãn v06 = `taxonomy.py`. **Phát hiện:** (1) manifest ghi `source_data_commit 5ce5796` ≠ commit ghim tài liệu `a086606` — zip không có git history nên **chưa xác minh được**, N2 xác nhận trước khi cập nhật submodule pointer; (2) `docs/DATA_PLAN.md` nói raw DOC/DOCX không commit, nhưng data nhận có HDLD001–006 raw (chỉ HDLD007 bị `.gitignore`) → đã sửa dòng đó thành cảnh báo, cần N2 + chủ BRD xác nhận de-identify/quyền phân phối; (3) HDLD006 chỉ có raw, chưa annotate. Số liệu split/hard test ghi ở `DATA_PLAN.md` §2a (phục vụ N2 làm "Kiểm kê D1", không thay việc đó) |
| 2026-10-23 | N4 | C-17/C-20 + mock API T1 (chưa có PR/commit) | Khác snapshot: `/contracts/upload` cũ có Postgres + SQL, được cắt khỏi app và loại bỏ stack legacy thay vì tiếp tục lưu text; `mock_clause_service` vẫn chỉ phục vụ contract N1. Dev trả kết quả giả đã de-identify qua session trong RAM; demo/eval fail-fast, admission/quota/lease và parsing thật chờ C-05/C-06. INV hiện có: schema ↔ enum, partition fixture, lifecycle/rejection/tombstone/retry/expiry; INV-01…12 của các stage chưa triển khai vẫn chờ. CI checkout submodule, không cần Gemini/DB/secret. |
| 2026-10-25 | N3 | Freeze risk taxonomy (21 nhãn, version risk_taxonomy_v01/severity_v01, fingerprint test), chuyển PII masking từ backend/privacy/pii_DRAFT.py sang backend/app/privacy/{pii_types,detector,masker}.py, test INV-01 + fixture tests/fixtures/privacy (chưa có PR) | Bỏ cột clause label tham khảo khỏi code (chỉ còn trong doc). Tham chiếu tên doc trong taxonomy.py đổi thành `docs/risk_taxonomy*.md`, test tự tìm doc. Detector chưa sửa gì; đã biết `detect` gán MST `0312345678` là PHONE thay vì LEGAL_ENTITY (fixture case_001 ghi đúng loại, để C-09 (b) đo). C-09 (b) còn lại ở T3 |
| 2026-10-25 | N1 | C-02, C-01 (a), freeze kỹ thuật clause taxonomy, CI `.github/workflows/ci.yml` (T2; chưa có PR/commit) | **Đã làm:** `backend/app/clause/{structure_parser,segmenter}.py`, `backend/app/domain/errors.py` (chỉ `ValidationReject`; N4 thêm các lỗi khác vào CÙNG file), xóa `ai_pipeline/utils/text_processing.py` (`document_router`), `ai_pipeline/test_pipeline.py` chạy qua `mask` → `segment`; test `tests/unit/test_{structure_parser,segmenter,clause_taxonomy_freeze}.py`, `tests/integration/test_segmenter_real_contracts.py`; fixture `tests/fixtures/segmentation/`; `docs/CLAUSE_TAXONOMY_FREEZE.md`; `pyproject.toml`: ruff `extend-exclude=ai_pipeline/data` + `.venv`, ignore E501 cho `test_pipeline.py` (**N4/C-20 chú ý khi merge**). **Quyết định kỹ thuật (đã ghi trong code):** (1) preamble trước heading đầu (quốc hiệu, thông tin các bên) là clause paragraph chứ không bị bỏ — mọi ký tự khác khoảng trắng thuộc đúng 1 clause; (2) heading nằm trong placeholder PII bị **bỏ** (không dời) — TDD §10.3 cho phép cả hai; (3) số có dấu phân cách nghìn (`2.000.000`, cả `5.100`) không là heading decimal; (4) list `n.`/`a)`/`-` chỉ thành clause khi ≥2 mục anh em và đánh số liên tiếp từ 1/a; (5) `boundary_guard` vẫn ở `privacy/masker.py` (N3), `segmenter` re-export — chưa chuyển để không sửa test của N3. **Số đo:** 6 hợp đồng thật → 40–68 clause (≤150), clause dài nhất 3.625 ký tự (<4.000); INV-02/03 pass; chưa chấm M1 (chưa có gold segmentation). **Phát hiện:** repo còn ~100 lỗi ruff ở file của người khác (E501, I001, E70x) — CI chặn cứng chỉ các đường dẫn sạch, toàn repo ở chế độ cảnh báo. `tests/test_data_lead_review.py` cần submodule → chạy ở job `data` riêng, tự bỏ qua nếu repo data private (đặt secret `SUBMODULE_TOKEN`). **Bổ sung (cùng ngày):** job `llm-live` thủ công (secret `GEMINI_API_KEY`) + `tests/llm/test_llm_live.py` (marker `llm`, mặc định bị bỏ qua) — hiện chỉ test service legacy, thêm test `classify()` khi C-01 (b) xong. **Còn mở:** sign-off N2/N3 cho policy đa nhãn + 3 topic (freeze doc §4); `classify()` C-01 (b) |
| 2026-10-26 | N4 | Ghi sai khác W1/W2 theo yêu cầu freeze docs; không sửa BRD/SRS/SDD/TDD hoặc bản split | **O-09:** SRS §6.2 thực tế đã có `INVALID_SESSION_STATE`, `SESSION_NOT_READY`, `SESSION_REJECTED`, `SESSION_EXPIRED`, `FEATURE_NOT_ENABLED`; TDD §5.1/§5.8/§21 vẫn nói chưa backport → đề xuất sửa mô tả TDD sau khi duyệt, không thêm code trùng ở SRS. **O-11:** hình `docs/diagrams/state_machine.png`/SDD §8 thiếu VALIDATING→FAILED và FAILED→VALIDATING khi retry local; bảng component thiếu Cleanup Scheduler, startup §13.1 đánh số 14–20 → đề xuất errata SDD/bản split. **BR-14:** BRD nói cập nhật kho luật phải sửa mã, trái SRS NFR-MAINT-03 → đề xuất cập nhật artifact dữ liệu version hóa không cần sửa mã, chờ chủ BRD duyệt. **DEC-17** chưa được nhóm chấp thuận; không tự phê duyệt. Runtime W2 hiện là dev sample (không extractor/LLM/corpus), `before_call` chỉ dành cho tích hợp provider; C-05 mới có barrier trên lease, chưa có barrier hai HTTP Create. |
| 2026-10-28 | N2 | C-12(a)/(b) offline, corpus skeleton + 5 điểm Điều 21 (branch `data/c12-legal-corpus-foundation`, local) | Đặt tại `data/legal_corpus/` theo TDD §14; `release_status=DRAFT` chặn runtime khi chưa Data/Legal sign-off. Thêm loader/validator/citation ID/checksum, chặn duplicate JSON/YAML, fixture và unit tests; retriever dùng label-map + BM25 (0.70/0.30), lọc hiệu lực/dedupe và seed/pool; **chưa nối runtime, chưa đo M8**. Nguồn: 45/2019/QH14 + VBHN 18/VBHN-VPQH 2026, chưa xác nhận từng mốc hiệu lực/từng thay đổi → không dùng làm căn cứ đánh giá hợp đồng. Danh mục P0/P1 là bản nháp, cần nhóm duyệt; PROGRESS OI-02 bị trùng mã khác nghĩa với SRS §13. Gold D1, OI-10/multilabel, C-13 và corpus đầy đủ còn mở. |
| 2026-10-28 | N2 | C-13(a) code offline (`data_graph.py`) | Build index hai chiều từ PARENT_OF canonical và REFERS_TO/GUIDES MANUAL trong fixture, filter endpoint có hiệu lực tại ngày phân tích; không load suggestion. Corpus thật vẫn DRAFT/0 manual edges; **C-13(a) chưa hoàn thành phần verified content; C-13(b) expand/rank/fallback để T5**. |
| 2026-10-31 | N4 | Đối chiếu API N5 tuần 2 trên `backend/n4-w3` (chưa có PR/commit) | **B1:** Retry trả cùng body Status; **B5:** Create/Status/Expired dùng UTC `Z`; **B4:** dev fixture `emoji.pdf` (đã có non-BMP), `insufficient.pdf` (null severity/không citation), `norisk.pdf` (điều khoản thường, không risk); **B6:** thiếu catalog message dùng thông báo INTERNAL_ERROR. **B2 xác nhận:** fixture `final_result_v1` có offset code point, span partition, nhãn hợp lệ, risk_basis 1:1, disclaimer/data_notice; test schema/fixture đã chạy. **B3 xác nhận:** TDD §6.4 trong repo hiện là `risk_taxonomy_v01`, khớp N3/code/fixture; đã sửa comment v02 cũ trong frontend types, không đổi taxonomy. **B7:** không thêm CORS vì Vite proxy cùng origin. **Chờ nhóm duyệt errata baseline:** body Retry ở TDD §5.5; stage/progress trạng thái cuối ở §5.3 (giữ nguyên hành vi hiện tại); SRS §6.2 `SESSION_NOT_ACCEPTING_UPLOAD` không có luồng upload vào session cũ trong API 6 operation, đề xuất ghi ngoài phạm vi sau khi chủ SRS duyệt. Không sửa BRD/SRS/SDD/TDD đã freeze. |
| 2026-10-31 | N4 | C-08(a), commit 1 trên `backend/n4-w3` | PDF-only `extract_pdf_v1`: sniff `%PDF-` + `.pdf`, cap 10MB/30 trang, 2 cột, header/footer ≥60%, flatten bảng, NFC/LF, quality gate gồm legacy-font; `extraction_v1` stage artifact giữ RAM. 264 passed / 4 skipped / 1 deselected trên suite offline bỏ test data lead; smoke PDF tiếng Việt tự tạo qua PyMuPDF: 1 trang, 158 code point, NFC. **Chưa D1** (data submodule rỗng), DOCX C-08(b) ở T4. Không sửa runtime Create/Orchestrator ở commit này; N1/N3/N5 review các thay đổi canonical trước khi tích hợp. |
| 2026-10-31 | N4 | C-10, commit 2 trên `backend/n4-w3` | `scope_precheck.precheck` thuần cục bộ, không LLM/không sửa canonical: title trong cửa sổ code point, cặp party, content/structure, negative thuần túy. 16 test C-10 pass; 280 passed / 4 skipped / 1 deselected trên suite offline bỏ test data lead; smoke 2 PDF tiếng Việt tự tạo qua extractor C-08(a): HĐLĐ accept (score 8), hóa đơn reject (score -3). OI-03 chưa chốt, không tune theo T1/T2; `NOT_LABOR_CONTRACT`/state sẽ nối trong commit 4. |
| 2026-10-31 | N4 | C-11, commit 3 trên `backend/n4-w3` | Đã rà references: chỉ `backend_architecture.md` còn mô tả Explanation AI như thành phần hiện tại; `backend/w1_report.md` là báo cáo lịch sử W1 nên giữ nguyên. Xóa adapter Explanation AI rỗng, sửa kiến trúc backend để phân biệt trạng thái hiện tại và luồng đích. 36 test lifecycle/contract pass; smoke HTTP dev 201 → COMPLETED → result 200 → End EXPIRED. Không thay đổi runtime API/pipeline. |
| 2026-11-01 | N1 | C-01 (b), C-07, prompt + adapter khung (T3; chưa có PR/commit) | **Quyết định/sai khác:** (1) model chỉ trả `items[{clause_id, clause_labels}]`; `schema_version/model_id/prompt_version/taxonomy_version` do backend điền để model không tự khai pin (INV-05) — lệch ví dụ TDD §13.2 (response có cả 4 trường), cần errata. (2) Retry ≤1 tính **chung** cho mọi loại lỗi của một lần gọi (TDD §13.4 ghi từng loại 'tối đa 1' — chọn cách bảo thủ để chặn quota/cost). (3) `prompt_version` = `clause_prompt_v1+v04+<sha8 prompt>`; (4) không dùng `asyncio.TaskGroup`/`asyncio.timeout` vì CI còn Python 3.10. (5) `requests` chỉ giới hạn từng lần đọc socket ⇒ thêm `asyncio.wait_for` làm timeout tổng. **Phát hiện:** `ai_pipeline/utils/text_processing.py` (`document_router`) và `ai_pipeline/config/__init__.py` (rỗng) **vẫn còn trong main** dù dòng 25/10 ghi 'đã xóa' (không file nào import) — đã xóa thật ở lượt này; `DailyQuota.before_call` chỉ tăng bộ đếm, **không chặn khi vượt quota** và chưa có `after_call` (N4, C-16); `domain/errors.py` thiếu `PipelineInternalError/LegalCorpusConflict`. Test chạy bằng shim offline (không cài được pytest) — cần chạy `pytest` thật + `ruff` trước khi mở PR |
| 2026-11-01 | N3 | C-09 (b), số đo PII, prompt `risk_v1` + `risk_adapter` khung (T3–T4 sớm; chưa có PR) | **Sửa:** MST có anchor lên high-precision trước PHONE; `_trim_name` chỉ cắt khi từ kế tiếp mở đầu nhãn (trước đó `Lê Quốc Huy` chỉ che `Lê`); SĐT bàn 02x. **Số đo:** nhóm A 16/16, nhóm B 23/25, preserve 29/29 trên 8 fixture TỔNG HỢP do N3 đánh gold — chỉ là tín hiệu hồi quy, D1 không có PII thật. **Risk:** model chỉ trả `schema_version/items`; pin (`model_id`, `prompt_version`, version taxonomy/severity) do backend đóng dấu; citation ngoài candidate chỉ đếm (`citations_outside_candidate`), lọc ở validator tuần 5; taxonomy nằm trong request (TDD §15.1) nên system prompt không lặp nhãn. Chưa làm (tuần 5): `detect_advice`, `sanitize_explanation`, citation validator. |
| 2026-11-01 | N3 | Nợ kỹ thuật sau W3 (chưa có PR; commit trên `n3-w3`) | **Quota/errors:** `DailyQuota.before_call` giữ chỗ nguyên tử (`try_reserve`) và raise `AI_PROVIDER_ERROR: QUOTA_EXHAUSTED` khi hết quota, có `after_call` ghi token/chi phí/lỗi (`daily_usage_detail`); thêm `PipelineInternalError`, `LegalCorpusConflict`. **Legacy đã xóa:** `clause_extraction_service.py`, `llm_clients.py` (key trong query string), `scripts/smoke_llm_pipeline.py`, `ai_pipeline/utils/`, stub `integrations/{clause,risk}_ai.py` (`document_router` và `ai_pipeline/config/` đã mất từ patch N1); CONTRIBUTING/README/doc đã sửa. **Test LLM:** `tests/llm/test_llm_live.py` chuyển sang adapter mới (Gemini); thêm `test_llm_local.py` (Ollama, marker `llm_local`) và `test_dev_local_client.py` (offline, chạy mặc định) — **chưa chạy được với Gemini/Ollama thật trong môi trường này**. **CI:** ruff chặn cứng toàn repo (trừ 2 file dữ liệu N2); job `data` đỏ khi không có submodule trên push/PR cùng repo. **Data:** áp `data.patch` (chỉ thêm `data/intake/`, mọi node `PENDING_LEGAL_REVIEW`, manifest 0 lỗi, 31 test dữ liệu pass), commit `6b35387` trong submodule và ghim; **phải push commit này lên repo data trước khi merge**. Pin `a086606` vs manifest `5ce5796`: đã đối chiếu, không lệch (xem `docs/DATA_PLAN.md`). Chưa làm: errata BR-14/DEC-17/TDD §5.5, §5.3, §13.2 (chủ tài liệu), lint 2 file dữ liệu N2, góp ý phạm vi/ID cho data intake (N2). |
| 2026-11-03 | N3 (audit tài liệu) | Đồng bộ PROGRESS với BRD 0.6, SRS 1.5, SDD 0.2, TDD 0.3 (bộ 5 patch); thêm X-12 đến X-29, cập nhật các mục chưa tick của T3 đến T7 | **Không đánh dấu ngược mục đã tick.** Freeze risk taxonomy 25/10 (đã tick) được mở lại: bản freeze vẫn là cơ sở của test hiện tại; X-15 sẽ đổi tên nhãn, rà severity rồi freeze lại. D1: dòng đề xuất 03/11 từng tính thêm HDLD005; quyết định nhóm 06/11 đã chốt HDLD001–004 (183) và HDLD005 thuộc T1 (xem BRD 0.6 §8.2). `risk_output_v2` và `final_result_v1` chỉ thêm trường tùy chọn, không đổi version. Hosting: hiện localhost. |
| 2026-11-07 | N1 | W4: classify_clauses hoàn thiện, C-14 (a), X-20 (N1), bộ chạy D1 + kết quả đo sơ bộ M7 trên Gemini | Đã chạy thật d1_clause_run.py với gemini-3.5-flash-lite: 4 HĐ ra 198 clause, 12 calls LLM thành công 100% (0 errors), tiêu tốn 22.411 in-tokens / 7.518 out-tokens. M7 sơ bộ đạt macro-F1 = 0.4974 (COMPENSATION_BENEFITS đạt 0.8378, INSURANCE_SAFETY đạt 0.70; các nhãn OBLIGATIONS và OTHER bị FP cao). M1 proxy đạt F1 = 0.5323. Toàn bộ 174/174 spans EXACT D1 khớp nội dung sau chuẩn hóa NFC. Hoàn tất toàn bộ deliverable Tuần 4 của N1. |

| 2026-11-06 | N2 | Owner-approved equivalent T1 gate and independent technical T1/T2 evaluation | `T1_EQUIVALENT_GATE_V1` admits 10/10 as 4 restricted + 5 template + 1 synthetic control; historical source-only intake remains 0/10; BRD 0.6 §8.2 adopts the equivalent gate. `reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/result.json` records M1 F1 (unique 8: 0.3683; real 9: 0.3713; composite 10: 0.3805; T2 nine: 0.3431), privacy §7.3 (21/21 PII, 62/63 fields preserved on nine T1 documents), T1 M7 Macro-F1 (747 full: 0.3377; 340 genuine: 0.5442), T2 M5 (12/30), T2 M8 Recall@5 (graph off 15/30; graph on 14/30), and M3a citation validity (T1 747/747; T2 387/387). BRD M4 is quote/offset correctness: T2 19/19 emitted risk outputs; T1 has zero emitted risk outputs, so M4 is undefined. Scores have 1,000 seed-0 document bootstrap intervals where defined. M7 is a newly fixed D1-only baseline; T2 privacy uses a derived reference not independently adjudicated. MS-4/MS-5 remain open; this row does not change the 19/19 early N2 checkbox count. |

## 2026-11-06 T1/T2 acceptance-threshold readout

See `reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/acceptance_readout.md` for the BRD threshold-by-threshold interpretation of the technical result. In brief: M1, M5, M7, and M8 are below threshold; M2, M3b, and M6 have no valid result in this run; M4 passes only for 19 emitted T2 risk outputs and is undefined on T1 because the baseline emitted no risk outputs. M3a's 100% is limited to corpus/effectivity membership of top-1 retrieved candidates. T1 privacy §7.3 point estimates pass; T2 privacy remains derived, not independently adjudicated. These results do not complete MS-4/MS-5 or the full Data Lead objective.
