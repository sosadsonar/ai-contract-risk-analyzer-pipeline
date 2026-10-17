<!-- nguồn: SDD_AI_Labor_Contract_Risk_Analyzer_v0.1.md | mục: 4. Pipeline xử lý end-to-end | 2026 ký tự | trước: 04_3-kien-truc-tong-the.md | sau: 06_5-thiet-ke-data-graph.md -->

# 4. Pipeline xử lý end-to-end

![](/diagrams/pipeline.png)

*Hình 3. Pipeline runtime đã refine ở mức SDD*

Pipeline giữ đúng các quy tắc của SRS: PII masking trước segmentation; masked_text cùng độ dài canonical_text; chỉ có hai bước LLM bắt buộc; legal retrieval chạy cục bộ; backend merge theo clause_id.

## 4.1 Trình tự Happy Path

1. API nhận role + PDF/DOCX, kiểm tra global processing lock, rate limit và quota.
2. Tạo session_id ngẫu nhiên, state = UPLOADED rồi chuyển VALIDATING.
3. Document Processing tạo canonical_text, chuẩn hóa NFC và kiểm tra chất lượng extraction.
4. Scope Precheck xác nhận HĐLĐ bằng luật cục bộ.
5. PII Masker tạo masked_text cùng độ dài canonical_text.
6. Clause Segmenter tách clause trên masked_text nhưng original_text lấy từ canonical_text theo cùng span.
7. Clause Graph Builder tạo NEXT, PARENT_OF, REFERS_TO bằng ID.
8. State chuyển PROCESSING; Clause Classification xử lý theo lô qua Gemini.
9. Baseline Retriever tạo seed legal candidates; Data Graph mở rộng tối đa 1 hop và lọc hiệu lực.
10. Clause Graph Context Resolver chọn related_clause_ids; backend lấy masked text tương ứng làm context cho Risk stage.
11. Risk LLM trả risk labels, severity/explanation/citation_ids/evidence_status theo clause_id.
12. Citation Validator loại citation không hợp lệ; Result Assembler ghép quote/span chuẩn.
13. Nếu toàn bộ stage thành công, state = COMPLETED; frontend lấy result/highlight/export.

## 4.2 Retry và lỗi

* REJECTED dùng cho input không hợp lệ/out-of-scope và là trạng thái cuối; muốn thử file khác phải mở session mới.
* FAILED dùng cho lỗi pipeline/provider; không expose partial result như final.
* LLM timeout 30 giây; auto-retry tối đa 1 lần cho một call.
* Manual retry tối đa 2 lần/session. Nếu stage resume còn được giữ, chỉ chạy lại từ stage lỗi khi toàn bộ version pin không đổi.
* Nếu Data Graph lỗi runtime, không fail toàn pipeline: fallback sang baseline retrieval và ghi RunLog.
* End Session phải hủy call đang chạy nếu có, xóa dữ liệu tạm và chuyển EXPIRED.
