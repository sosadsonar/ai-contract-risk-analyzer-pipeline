# Data Plan — Contract Risk Analyzer

Owner: Data Lead (Người 2). Cập nhật: 17/10/2026 theo `DATA_LEAD_REVIEW_V03.md`.
Trạng thái: **thay bản Tuần 1 (v1)** — bản đó đã lỗi thời (8 nhãn, dữ liệu tổng hợp, mục tiêu 40–50 HĐ, ngưỡng `t_low/t_high`, `document_router`) và mâu thuẫn BRD 0.5 §8.2 (SRS Phụ lục C, C-19).

## 1. Nguồn chân lý về dữ liệu đánh giá

Kế hoạch tập dữ liệu, chỉ số và quy tắc đánh giá **không** định nghĩa ở file này mà ở:

- **BRD 0.5 §8.2** — D1 / D2 / T1 / T2 (số HĐ, mục đích, quy tắc 1–7); **§8.3** chỉ số M1–M8, BL-1; **§8.4** lỗi chèn.
- **SRS 1.4** — DEC-10 (đóng băng clause taxonomy, risk taxonomy, severity rubric, annotation guideline ở MS-1, 25/10/2026), OI-10 (chính sách đa nhãn).
- **TDD 0.2 §18** — định dạng gold (`seg/clause/risk/injected/privacy/...`), harness, ánh xạ metric.

Quy tắc cứng: **không chỉnh hệ thống dựa trên T1/T2**; tuning chỉ trên D1/D2.

## 2. Hiện trạng dataset (kiểm ngày 12–17/10/2026)

| Mục | Giá trị kiểm được |
|---|---|
| Data repo | submodule `ai_pipeline/data`, ghim commit `a086606d8ffe1e4bce90845c40513d94cb8800dc` (Data PR #8); không dùng `submodule update --remote`, không sửa file data từ repo pipeline |
| Dataset | `clauses_v06.csv`, 234 clause, 5 hợp đồng đã annotate, 4 template family |
| Chất lượng offset | 225 `EXACT` + 9 `CONTEXT` (audit: `data_lead_span_audit.json`) |
| Annotation lịch sử | 183 annotation giữ nguyên nội dung/nhãn khi đối chiếu v04 → v06 |
| Taxonomy | 12 nhãn, semantics nguồn `clause_taxonomy_v03.md` (data repo); code `TAXONOMY_VERSION = v04` (chỉ sửa định nghĩa prompt) |
| Gold rủi ro pháp lý | **chưa có** (`null`) |
| Split dev/test | provisional theo nhóm hợp đồng; test đang nằm công khai trong repo; thiếu WORKING_TIME ở test, thiếu TERMINATION ở dev → **chưa phải test giữ kín** |
| `synthetic_v0.2.json` | 6 HĐ / 27 clause, chỉ là smoke fixture (CONTRIBUTING §5); **không** tính vào KPI/benchmark |
| Dữ liệu thô | ⚠️ **Lệch (đối chiếu 20/10)**: data nhận ngày 20/10 có `data/raw/contracts/HDLD001–006` (`.doc`/`.docx`) nằm trong repo; `.gitignore` của data repo chỉ còn loại HDLD007 (chờ quyền phân phối). Cần Người 2 + chủ BRD xác nhận các file này đã de-identify/được phép phân phối (BRD 7.6, OI-03) — pipeline không tự quyết |

### 2a. Đối chiếu data nhận ngày 20/10/2026 (`data.zip` = release `v06-rc1`)

Đã kiểm trong repo pipeline (`ai_pipeline/data/`): 30/30 hash trong `data/releases/v06-rc1/manifest.json` khớp; `validate_dataset.py` 0 lỗi; test data repo 28 pass + 1 skip; test của Data Lead (`tests/test_data_lead_review.py`) pass đủ; 12 nhãn của `clauses_v06.csv` **trùng đúng** `backend/app/clause/taxonomy.py`. Các số liệu ở bảng §2 đều khớp (234 clause, 225 EXACT + 9 CONTEXT, 5 HĐ đã annotate).

| Mục | Giá trị trong data nhận |
|---|---|
| Release | `v06-rc1`, `CANDIDATE_REVIEW_REQUIRED`; manifest ghi `source_data_commit 5ce5796`, `base_main_commit 3fadcfe`. **Chưa đối chiếu được với commit ghim `a086606`** (file zip không có lịch sử git) |
| Hợp đồng | 6 raw: HDLD001–005 đã annotate (39/40/61/43/51 clause); **HDLD006** giữ raw để kiểm duplicate (gần trùng HDLD005, chưa annotate); **HDLD007** chờ quyền phân phối + annotate |
| Split provisional | train HDLD003+005 (112) · dev HDLD001+002 (79, scorable 49) · test HDLD004 (43, scorable 34); span EXACT scorable 110/48/28. Dev thiếu `TERMINATION`, test thiếu `WORKING_TIME` (đã xác nhận bằng số) |
| Hard test | `hard_test_v06_rc1.jsonl`, 20 ca (14 EXACT + 6 CONTEXT), chờ adjudicate độc lập; nhãn pháp lý = null |
| Blocker do data repo tự ghi | adjudication hard test; thiếu nhãn dev/test ở trên; review semantic leakage; chưa có ground truth rủi ro pháp lý |
| Lưu ý kỹ thuật | `.gitattributes` ép LF cho raw text/CSV/manifest — **không đổi newline** trước khi áp offset (offset là code point trên đúng bản hash) |

Chưa đạt so với kế hoạch Tuần 5 cũ: số hợp đồng (5 so với mốc 30+ của bản v1) — mốc đó **không còn hiệu lực**; mốc hiện hành là T1 ≥ 10 HĐ gốc (BRD 8.2).

## 3. Annotation guideline (giữ lại; đóng băng ở MS-1)

Guideline đầy đủ: data repo (annotation guideline v1.0 + `clause_taxonomy_v03.md`). Tóm tắt phần ảnh hưởng tới pipeline:

1. Một **Điều** có thể chứa nhiều clause; câu/bullet đa chủ đề được **tách** thành nhiều clause thay vì gán đa nhãn. Một dòng dataset = **một nhãn**.
2. `clause_text` **không** gồm heading "Điều X. …" và không gồm phần hành chính (Rule 5, 6).
3. Offset tính theo **Unicode code point**, `[start, end)`, trên đúng raw text đã hash (không tính theo dòng).
4. `offset_quality`: `EXACT` = đoạn khớp nguyên văn sau gom khoảng trắng; `CONTEXT` = annotation lặp ngữ cảnh sau khi tách nên không có đoạn nguyên văn. `CONTEXT` giữ `span = null` ở consumer, **không** ép `_locate_span` tìm đoạn giả và **không** chấm như gold span chính xác; có thể dùng source-reference span riêng để highlight.
5. Không bịa mức/điều kiện vào chỗ trống trong hợp đồng; không dùng định nghĩa nhãn để suy ra mức rủi ro pháp lý.
6. Hợp đồng thật: bắt buộc de-identify thủ công; hợp đồng mới nên có ít nhất 1 clause "khó"; cần ≥ 20% item do hai người gán độc lập để tính Cohen's kappa (BRD 8.2 quy tắc 4).

## 4. Dùng dataset này trong pipeline mới (cần nhóm chốt)

- Dataset là gold **nhãn clause**. Gold **segmentation** cho M1 vẫn do người sửa tay ranh giới (BRD 8.2 quy tắc 3) vì dataset bỏ heading và tách trong Điều, không phải partition không chồng lấn của `canonical_text`.
- Quy đổi single-label (dataset) ↔ 1–3 nhãn/clause (pipeline, SRS OI-10) khi tính M2/M7 chưa có chính sách → cần chốt cùng annotation guideline trước MS-1.
- `ai_pipeline/eval/fixtures/build_golden_v0_3.py` còn đọc `clauses_v02` không có offset: cần Evaluation Lead cập nhật adapter v06, masks và policy `CONTEXT` trước khi tính F1 (TDD §18.3).

## 5. Versioning dữ liệu

- `golden_v0.1.json`, `golden_v0.2.json` (Tuần 1; taxonomy 8 nhãn cũ): **giữ làm lịch sử**, không dùng cho KPI.
- Data repo: các bản `clauses_v0x.csv` tăng version khi đổi đáng kể số lượng/taxonomy/offset; không sửa đè bản cũ. Report audit ghi cả hash file đọc thực tế và hash Git blob (khác nhau do CRLF/LF trên Windows).

## 6. Còn mở

- D1 trong BRD 8.2 (4 HĐ / 183 điều khoản) so với data hiện có (5 HĐ / 234 clause): xác nhận D1 gồm gì rồi mới sửa BRD.
- Mở rộng template/coverage; provenance HDLD001–003; quyền chia sẻ HDLD007; hard-gold adjudication; khóa split và giữ kín T1.
- Topic bảo mật/không cạnh tranh và giải quyết tranh chấp (xem `CLAUSE_TAXONOMY.md` §3).
