# Data Lead pipeline integration review — 14/11/2026

> tôi fix xong hết mới merge lên 1 lần nên hơi boom tí

## Phạm vi

Nhánh tích hợp này ghép phần Pipeline Data Lead đã commit đến `e3f8ca8` với
`origin/main` tại `85474ca`. Diff lớn vì bao gồm các lớp parser, phân loại,
truy xuất luật, runner, bộ chấm, kiểm thử và báo cáo phiên bản từ nhiều tuần.
Các tệp làm việc chưa commit ở hai checkout gốc không nằm trong nhánh này.

## Kết quả có thể dùng

| Hạng mục | Bằng chứng hiện tại | Giới hạn |
| --- | --- | --- |
| M1 | D2 v02 Dev F1 0,9066 tại IoU ≥ 0,80 | T1 held-out 0,3718; khác quy ước Gold. |
| M2 | D1 v04 + D2 Dev, sáu nhãn có Gold: Macro-F1 0,9708 | Baseline cục bộ; T1 v02 chỉ hai nhãn có Gold, F1 0,3333. |
| M5 | D2 Dev 30/30 | T2 read-only 26/30; chưa đạt 27/30. |
| M6 | Gói D2 Dev 40 mẫu: A/B 39/40, κ 0,9310; 40/40 khớp runner v1.3 | Chưa có mẫu nghiệm thu held-out. |
| M8 | D1/D2 Dev Graph Off 66/74, On 74/74 | D1 oracle 14/14 On; thiếu D2 clause-label oracle. |

M3a và M4 chứng minh tính hợp lệ cấu trúc của trích dẫn và offset trên output
đã phát. Chúng không tự chứng minh tính đúng đắn pháp lý của kết luận rủi ro.
`PRODUCT_RUNNER_ENABLED` vẫn là cờ opt-in; chưa có bằng chứng chạy Gemini thật
cho toàn bộ 21 nhãn. Không dùng các điểm Dev như điểm nghiệm thu held-out.

## Kiểm tra tích hợp

- Ghép vào `origin/main` bằng Git merge sạch, không có conflict.
- `.venv` Pipeline `pytest -q`: exit 0; test cần private submodule được skip.
- `.venv` Pipeline `ruff check .`: exit 0.
- `git diff --check origin/main...HEAD`: exit 0.
- Đã ghim LF cho `dev_injection_candidate.py` trong `.gitattributes` để
  SHA-256 bytes của bộ dò giữ `a6d7a1fb2663511764606d0ad9075246df423a282eb96c406fca342c6644f438`
  kể cả khi Git trên Windows đặt `core.autocrlf=true`; mã detector không đổi.
- Không đưa CSV duyệt, Gold restricted, văn bản hợp đồng hoặc tệp `.env` vào PR.

## Điều kiện trước merge

Theo `CONTRIBUTING.md` §4.5, cần ít nhất một reviewer độc lập và CI xanh.
Reviewer kiểm tra đặc biệt: scope Dev/held-out trong báo cáo, ranh giới dữ liệu,
ánh xạ `WORKING_CONDITIONS -> Điều 17 khoản 1`, đường Graph On trong runner,
và checksum bất biến của `dev_injection_candidate.py`.

Repo Data có PR #19/#20 đang mở và nhánh Data Lead địa phương lệch `main`;
đây là luồng review riêng. Không cập nhật submodule sang một commit Data chưa
được nhóm duyệt và push.
