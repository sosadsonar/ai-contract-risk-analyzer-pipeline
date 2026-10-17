<!-- nguồn: SDD_AI_Labor_Contract_Risk_Analyzer_v0.1.md | mục: 14. Evaluation Architecture | 501 ký tự | trước: 14_13-deployment-architecture.md | sau: 16_15-traceability-srs-component.md -->

# 14. Evaluation Architecture

Evaluation Harness dùng cùng các module pipeline nhưng chạy như thư viện ngoại tuyến, không qua API/session runtime.

* Input: D1/D2/T1/T2 đã de-identify thủ công.
* Output: JSON artifacts và metrics M1-M8; không bị session cleanup xóa.
* M8 phải chạy hai cấu hình: Data Graph enabled và disabled.
* Judge Claude là tool offline riêng; chỉ chạy sau calibration M6 và không nằm trong product API.
* Mọi output evaluation chứa version pins và commit hash theo EV-04/EV-07.
