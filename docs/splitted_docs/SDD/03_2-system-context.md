<!-- nguồn: SDD_AI_Labor_Contract_Risk_Analyzer_v0.1.md | mục: 2. System Context | 743 ký tự | trước: 02_1-muc-dich-va-nguyen-tac-thiet-ke.md | sau: 04_3-kien-truc-tong-the.md -->

# 2. System Context

Hệ thống gồm web frontend, một backend duy nhất, kho luật nội bộ, Gemini Flash là LLM sản phẩm và một evaluation harness ngoại tuyến. Claude chỉ dùng cho đánh giá, không nằm trong product runtime.

![](/docs/diagrams/system_context.png)

*Hình 1. System Context*

## 2.1 Trust boundary

* Browser -> Backend: dữ liệu gốc có PII, bắt buộc HTTPS trong môi trường deploy.
* Trusted Backend: được phép giữ canonical text trong session tạm thời và thực hiện extraction, masking, segmentation, graph build, retrieval, assembly.
* Backend -> Gemini: chỉ masked text và metadata cần thiết; không gửi raw/canonical text chưa che.
* Evaluation Harness -> Claude: chỉ dữ liệu đã che hoặc đã de-identify; không có API judge trong sản phẩm.
