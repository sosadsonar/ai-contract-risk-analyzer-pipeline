<!-- nguồn: PII_MEASUREMENT_2026-11-01.md | mục: Số đo PII đầu tiên (C-09 b, MS-2) > 2. Recall khi che (gold span phải được phủ 100%) | 651 ký tự | trước: 01_1-nguon-gold-va-co-mau.md | sau: 03_3-ty-le-giu-nguyen-truong-can-giu.md -->

## 2. Recall khi che (gold span phải được phủ 100%)

| Nhóm | Gold | Đã che | Recall | Ngưỡng | Kết quả |
|---|---|---|---|---|---|
| A (CCCD/hộ chiếu, SĐT, email, TK ngân hàng) | 16 | 16 | 100.0% | ≥ 99% | ĐẠT |
| B (họ tên, ngày sinh, địa chỉ, pháp nhân) | 25 | 23 | 92.0% | ≥ 90% | ĐẠT |

Theo loại (đúng loại = span dự đoán cùng loại phủ cả gold span):

| Loại | Gold | Đã che | Đúng loại |
|---|---|---|---|
| BANK_ACCOUNT | 2 | 2 | 2 |
| DATE_OF_BIRTH | 2 | 2 | 2 |
| EMAIL | 4 | 4 | 4 |
| LEGAL_ENTITY | 6 | 6 | 6 |
| NATIONAL_ID_OR_PASSPORT | 3 | 3 | 3 |
| PERSON_NAME | 12 | 11 | 11 |
| PHONE | 7 | 7 | 7 |
| RESIDENTIAL_ADDRESS | 5 | 4 | 4 |
