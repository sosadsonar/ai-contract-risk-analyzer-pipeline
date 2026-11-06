<!-- nguồn: PII_MEASUREMENT_2026-11-01.md | mục: Số đo PII đầu tiên (C-09 b, MS-2) > 1. Nguồn gold và cỡ mẫu | 463 ký tự | trước: 00_so-do-pii-dau-tien-c-09-b-ms-2.md | sau: 02_2-recall-khi-che-gold-span-phai-duoc-phu-100.md -->

## 1. Nguồn gold và cỡ mẫu

- Fixture tổng hợp `tests/fixtures/privacy/case_*.json`: 8 ca, gold span do N3 đánh dấu tay (không phải hợp đồng thật, không phải gold của N2). Cỡ mẫu nhỏ: một span sót làm recall nhóm đổi vài điểm phần trăm, nên các con số dưới đây là **tín hiệu hồi quy, chưa phải số nghiệm thu**.
- D1: 6 mẫu đã de-identify (biểu mẫu trống), **không có PII thật** nên không đo được recall trên D1. Gold privacy D1 (N2) và T1 (hợp đồng thật) chưa có.
