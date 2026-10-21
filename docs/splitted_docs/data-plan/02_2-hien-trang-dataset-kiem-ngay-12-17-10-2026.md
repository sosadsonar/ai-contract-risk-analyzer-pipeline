<!-- nguồn: DATA_PLAN.md | mục: Data Plan — Contract Risk Analyzer > 2. Hiện trạng dataset (kiểm ngày 12–17/10/2026) | 1298 ký tự | trước: 01_1-nguon-chan-ly-ve-du-lieu-danh-gia.md | sau: 03_3-annotation-guideline-giu-lai-dong-bang-o-ms-1.md -->

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
| Dữ liệu thô | `data/raw/`, `*.pdf`, `*.docx` không commit (`.gitignore`); hợp đồng thật phải de-identify trước khi vào repo |

Chưa đạt so với kế hoạch Tuần 5 cũ: số hợp đồng (5 so với mốc 30+ của bản v1) — mốc đó **không còn hiệu lực**; mốc hiện hành là T1 ≥ 10 HĐ gốc (BRD 8.2).
