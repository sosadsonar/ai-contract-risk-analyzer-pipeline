<!-- nguồn: DATA_LEAD_REVIEW_V03.md | mục: Data Lead review cho PR #2 — 12/10/2026 > Tiến độ tuần 5 so với kế hoạch gốc | 1307 ký tự | trước: 03_audit-9-unmatched-span.md | sau: 05_kiem-thu-va-blockers-tich-hop.md -->

## Tiến độ tuần 5 so với kế hoạch gốc

Nguồn kế hoạch: `docs/DATA_PLAN.md` §3, tại main pipeline `18e56be`.

| Mục tiêu tuần 5 | Thực tế kiểm được | Trạng thái |
|---|---|---|
| 30+ hợp đồng | v06: 5 hợp đồng annotate, 4 template family | Chưa đạt; thiếu ít nhất 25 hợp đồng so với mốc tối thiểu |
| Khoảng 150–200 clause | v06: 234 clause | Đạt khối lượng; chưa đủ đa dạng hợp đồng |
| Clause Detection F1 ≥0.85 / Risk Macro-F1 ≥0.80 đáng tin cậy | Chưa có model metrics được kiểm chứng; legal-risk gold chưa có | Chưa nghiệm thu |
| Tách dev và test giữ kín từ tuần 5 | Có provisional group split; test đã nằm công khai trong repo; thiếu WORKING_TIME test và TERMINATION dev | Có split/masks, chưa phải test giữ kín đã khóa |

6 hợp đồng / 27 clause ở `synthetic_v0.2.json` là smoke fixture theo
CONTRIBUTING §5 và không được dùng để nhận KPI đã đạt. Không gộp chúng vào
5 hợp đồng thật đã annotate để tuyên bố benchmark đáp ứng mốc 30+.

Phần Data đã hoàn thành: QC và phân bố nhãn, raw/offset, duplicate masks,
hard candidate 20 ca có nguồn, release candidate/hash, tài liệu bàn giao,
đối chiếu taxonomy và audit 9 span. Còn mở: hard-gold adjudication, mở rộng
template/coverage, provenance HDLD001–003, quyền chia sẻ HDLD007 và đo model.
Vì vậy chưa thể xác nhận toàn bộ tiến độ tuần 5 đã đạt kế hoạch.
