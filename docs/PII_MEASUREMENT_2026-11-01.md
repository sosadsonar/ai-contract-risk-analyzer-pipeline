# Số đo PII đầu tiên (C-09 b, MS-2)

Phiên bản masking: `pii_draft_0.3`. Ngưỡng: BRD §7.3 (mục tiêu demo, không phải cam kết).
Sinh bởi `python ai_pipeline/eval/eval_pii.py`; số liệu đổi khi detector/fixture đổi.

## 1. Nguồn gold và cỡ mẫu

- Fixture tổng hợp `tests/fixtures/privacy/case_*.json`: 8 ca, gold span do N3 đánh dấu tay (không phải hợp đồng thật, không phải gold của N2). Cỡ mẫu nhỏ: một span sót làm recall nhóm đổi vài điểm phần trăm, nên các con số dưới đây là **tín hiệu hồi quy, chưa phải số nghiệm thu**.
- D1: 6 mẫu đã de-identify (biểu mẫu trống), **không có PII thật** nên không đo được recall trên D1. Gold privacy D1 (N2) và T1 (hợp đồng thật) chưa có.

## 2. Recall khi che (gold span phải được phủ 100%)

| Nhóm | Gold | Đã che | Recall | Ngưỡng | Kết quả |
| :--- | ---: | ---: | ---: | ---: | :--- |
| A (CCCD/hộ chiếu, SĐT, email, TK ngân hàng) | 16 | 16 | 100.0% | ≥ 99% | ĐẠT |
| B (họ tên, ngày sinh, địa chỉ, pháp nhân) | 25 | 23 | 92.0% | ≥ 90% | ĐẠT |

Theo loại (đúng loại = span dự đoán cùng loại phủ cả gold span):

| Loại | Gold | Đã che | Đúng loại |
| :--- | ---: | ---: | ---: |
| BANK_ACCOUNT | 2 | 2 | 2 |
| DATE_OF_BIRTH | 2 | 2 | 2 |
| EMAIL | 4 | 4 | 4 |
| LEGAL_ENTITY | 6 | 6 | 6 |
| NATIONAL_ID_OR_PASSPORT | 3 | 3 | 3 |
| PERSON_NAME | 12 | 11 | 11 |
| PHONE | 7 | 7 | 7 |
| RESIDENTIAL_ADDRESS | 5 | 4 | 4 |

## 3. Tỷ lệ giữ nguyên trường cần giữ

29/29 = **100.0%** (ngưỡng ≥ 95%): ĐẠT. Trường bị che nhầm: 0.

Span dự đoán không chạm gold nào (che thừa): 0.

## 4. Span sót (giới hạn đã biết, đưa vào quyết định OI-12)

- case_008 PERSON_NAME: `Lê Văn Cường`
- case_008 RESIDENTIAL_ADDRESS: `số 5 ngõ 7 phố Huế, quận Hai Bà Trưng, Hà Nội`

## 5. D1: kiểm tra che nhầm và quét lỏng

| Tệp | Code point | Span | Ký tự bị đổi | Quét lỏng (9-13 số / email / SĐT) |
| :--- | ---: | ---: | ---: | :--- |
| HDLD001.txt | 7213 | 0 | 0 | 0 / 0 / 0 |
| HDLD002.txt | 6822 | 0 | 0 | 0 / 0 / 0 |
| HDLD003.txt | 9004 | 0 | 0 | 0 / 0 / 0 |
| HDLD004.txt | 10991 | 0 | 0 | 0 / 0 / 0 |
| HDLD005.txt | 14402 | 0 | 0 | 0 / 0 / 0 |
| HDLD006.txt | 13090 | 0 | 0 | 0 / 0 / 0 |

0 span và 0 kết quả quét lỏng nghĩa là D1 đã sạch PII và detector không che nhầm; điều này **không** chứng minh recall.

## 6. Kết luận cho quyết định OI-12 (local NER)

- Trên fixture tổng hợp, regex/heuristic đạt cả hai nhóm và tỷ lệ giữ nguyên, **nhưng** fixture do chính người viết detector đánh dấu và chỉ có 2 ca giới hạn cố ý (tên không anchor, địa chỉ không anchor). Con số này không đại diện cho hợp đồng thật.
- Điểm yếu cấu trúc còn lại là nhóm B không có anchor: tên và địa chỉ đứng trong câu văn thường (vd. người liên hệ, nơi cư trú trong điều khoản). Regex không bắt được; chỉ NER hoặc gold thật mới đo được.
- Đề xuất cho MS-2: **chưa chốt bỏ NER**. Điều kiện chốt: chạy lại script này trên gold privacy D1 (N2) hoặc 2-3 hợp đồng thật đã gán span (T1). Nếu nhóm B < 90% trên gold thật thì mở local NER (OI-12); nếu ≥ 90% thì giữ regex và ghi giới hạn vào thông báo người dùng (BRD §7.6).
- Rủi ro rò rỉ lớn nhất không nằm ở số đo: placeholder cùng độ dài nên LLM thấy được độ dài tên; và tên pháp nhân bị che nhưng từ vai trò giữ nguyên (đúng thiết kế TDD §10.2).
