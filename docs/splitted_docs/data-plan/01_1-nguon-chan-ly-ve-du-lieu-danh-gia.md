<!-- nguồn: DATA_PLAN.md | mục: Data Plan — Contract Risk Analyzer > 1. Nguồn chân lý về dữ liệu đánh giá | 580 ký tự | trước: 00_data-plan-contract-risk-analyzer.md | sau: 02_2-hien-trang-dataset-kiem-ngay-12-17-10-2026.md -->

## 1. Nguồn chân lý về dữ liệu đánh giá

Kế hoạch tập dữ liệu, chỉ số và quy tắc đánh giá **không** định nghĩa ở file này mà ở:

- **BRD 0.5 §8.2** — D1 / D2 / T1 / T2 (số HĐ, mục đích, quy tắc 1–7); **§8.3** chỉ số M1–M8, BL-1; **§8.4** lỗi chèn.
- **SRS 1.4** — DEC-10 (đóng băng clause taxonomy, risk taxonomy, severity rubric, annotation guideline ở MS-1, 25/10/2026), OI-10 (chính sách đa nhãn).
- **TDD 0.2 §18** — định dạng gold (`seg/clause/risk/injected/privacy/...`), harness, ánh xạ metric.

Quy tắc cứng: **không chỉnh hệ thống dựa trên T1/T2**; tuning chỉ trên D1/D2.
