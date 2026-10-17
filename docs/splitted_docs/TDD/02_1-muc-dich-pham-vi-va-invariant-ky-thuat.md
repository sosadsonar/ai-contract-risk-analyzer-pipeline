<!-- nguồn: TDD_AI_Labor_Contract_Risk_Analyzer_v0.2.md | mục: 1. Mục đích, phạm vi và invariant kỹ thuật | 1676 ký tự | trước: 01_kiem-soat-tai-lieu.md | sau: 03_2-cac-quyet-dinh-ky-thuat-tdd.md -->

# 1. Mục đích, phạm vi và invariant kỹ thuật

TDD chuyển SRS 1.3 và SDD 0.1 thành các hợp đồng kỹ thuật đủ cụ thể để triển khai và kiểm thử. Các chi tiết dưới đây ưu tiên tính đơn giản, truy vết và khả năng hoàn thành trong 8 tuần xây dựng; không tối ưu theo tiêu chuẩn production.

## 1.1 Invariant không được phá

* Canonical text là nguồn duy nhất cho quote, span, highlight và export quote.
* PII masking chạy trên toàn canonical_text trước segmentation; len(masked_text) == len(canonical_text).
* canonical_text[start_char:end_char] == original_text cho mọi clause; ranh giới không nằm trong placeholder.
* Chỉ masked text được phép ra khỏi trusted backend tới Gemini; LLM không sinh hoặc sửa quote/span.
* Mọi output AI join bằng clause_id. Backend sở hữu state, span, citation validation và final assembly.
* Legal retrieval chạy local; citation chỉ thuộc candidate list, closed corpus và phiên bản hiệu lực tại analysis_date.
* INSUFFICIENT_EVIDENCE => citation_ids rỗng và severity = null.
* Clause Graph chỉ chứa clause_id + edge_type; không chứa contract text và không thay đổi segmentation/span.
* Nội dung hợp đồng/session không lưu bền vững; restart backend làm mất session content.
* Một phiên VALIDATING/PROCESSING tại một thời điểm; REJECTED không retry, FAILED retry thủ công tối đa 2 lần.

## 1.2 Non-goals của TDD

* Không thêm chatbot, user account, missing-clause detection, OCR, mobile app, fine-tune/self-host model.
* Không dùng graph database hoặc microservice cho demo.
* Không đưa advice/suggestion sửa điều khoản vào prompt, API response hay export.
* Không định nghĩa lại M1-M8, BL-1 hay ngưỡng PII; TDD chỉ cung cấp artifact để đo các chỉ số đó.
