<!-- nguồn: DATA_PLAN.md | mục: Data Plan — Contract Risk Analyzer > 2. Hiện trạng dataset (kiểm ngày 12–17/10/2026) | 3355 ký tự | trước: 01_1-nguon-chan-ly-ve-du-lieu-danh-gia.md | sau: 03_3-annotation-guideline-giu-lai-dong-bang-o-ms-1.md -->

## 2. Hiện trạng dataset (kiểm ngày 12–17/10/2026)

| Mục | Giá trị kiểm được |
|---|---|
| Data repo | submodule `ai_pipeline/data`, ghim commit `6b35387`; không dùng `submodule update --remote`, không sửa file data từ repo pipeline |
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
| Release | `v06-rc1`, `CANDIDATE_REVIEW_REQUIRED`; manifest ghi `source_data_commit 5ce5796`, `base_main_commit 3fadcfe`. **Đã đối chiếu (01/11, bằng git trong submodule):** `5ce5796` là tổ tiên của `a086606` và `6b35387`; 30/30 hash manifest khớp tại cả hai commit; `clauses_v06.csv`, 6 raw_text, 6 raw contract, taxonomy v03 và guideline giống hệt byte với `5ce5796`; các tệp còn lại (metadata, split, báo cáo W5, manifest) được thêm/sửa SAU `5ce5796` trong chính các PR release nên không có ở commit đó. Kết luận: pin không phá manifest |
| Hợp đồng | 6 raw: HDLD001–005 đã annotate (39/40/61/43/51 clause); **HDLD006** giữ raw để kiểm duplicate (gần trùng HDLD005, chưa annotate); **HDLD007** chờ quyền phân phối + annotate |
| Split provisional | train HDLD003+005 (112) · dev HDLD001+002 (79, scorable 49) · test HDLD004 (43, scorable 34); span EXACT scorable 110/48/28. Dev thiếu `TERMINATION`, test thiếu `WORKING_TIME` (đã xác nhận bằng số) |
| Hard test | `hard_test_v06_rc1.jsonl`, 20 ca (14 EXACT + 6 CONTEXT), chờ adjudicate độc lập; nhãn pháp lý = null |
| Blocker do data repo tự ghi | adjudication hard test; thiếu nhãn dev/test ở trên; review semantic leakage; chưa có ground truth rủi ro pháp lý |
| Lưu ý kỹ thuật | `.gitattributes` ép LF cho raw text/CSV/manifest — **không đổi newline** trước khi áp offset (offset là code point trên đúng bản hash) |

Chưa đạt so với kế hoạch Tuần 5 cũ: số hợp đồng (5 so với mốc 30+ của bản v1) — mốc đó **không còn hiệu lực**; mốc hiện hành là T1 ≥ 10 HĐ gốc (BRD 8.2).
