<!-- nguồn: TDD_AI_Labor_Contract_Risk_Analyzer_v0.3.md | mục: Phụ lục C. Prompt contract | 2118 ký tự | trước: 24_phu-luc-b-env-example.md | sau: 26_phu-luc-d-checklist-truoc-khi-khoa-demo.md -->

# Phụ lục C. Prompt contract

## C.1 Clause prompt - bắt buộc

* Nhận `clause_id + masked_text`; **không role**, canonical original/span.
* Chọn 1-3 labels từ taxonomy version.
* Không risk/advice/confidence.
* Provider structured output theo `clause_output_v3`, không Markdown.

## C.2 Risk prompt - bắt buộc

* Nhận role, target masked clause, clause labels, candidate IDs/catalog và optional related clauses.
* Risk taxonomy đi kèm label + definition và định nghĩa ba `basis_type`; model chọn label và `basis_type`, backend kiểm theo taxonomy, dựng `risk_basis` và tra severity.
* Chỉ clause hiện có; không missing-clause risk.
* Citation chỉ candidate IDs. Không nhớ/viện dẫn luật ngoài candidate.
* Thiếu căn cứ -> INSUFFICIENT_EVIDENCE, severity null, citations empty. Áp dụng cho cả ba basis_type; nghi LEGAL_VIOLATION mà không có candidate phù hợp thì vẫn chọn LEGAL_VIOLATION kèm INSUFFICIENT_EVIDENCE.
* Định nghĩa UNFAVORABLE và AMBIGUOUS theo vai trò (BRD 3.2: N1 đến N3, E1 đến E3; AMBIGUOUS gồm thiếu số liệu hoặc điều kiện và mâu thuẫn giữa hai điều khoản), kèm 4 đến 6 ví dụ neo cho cả hai phía do người phụ trách dữ liệu xác minh. Phân tích như thể điều khoản có hiệu lực.
* Quy tắc cận chắc chắn: chỉ kết luận LEGAL_VIOLATION khi giá trị vượt mức nới nhất của mọi trường hợp (ví dụ lương dưới mức vùng IV; thử việc quá 180 ngày). Khoảng giữa dựa vào clause JOB_INFO trong context (Điều 25 có bốn mức 180, 60, 30 và 6 ngày); thiếu thông tin thì AMBIGUOUS.
* Khi hai clause trong context mâu thuẫn nhau: basis_type AMBIGUOUS, điền `related_clause_ids` (tập con của context) và nêu mâu thuẫn trong explanation.
* Trong explanation: nhắc luật kèm tên văn bản ("Điều 97 Bộ luật Lao động 2019"), gọi điều khoản hợp đồng là "điều khoản số N của hợp đồng"; nhắc điểm của khoản bằng lời, không chép lại nội dung điểm.
* related_clauses chỉ context cho điều kiện/phụ thuộc/mâu thuẫn; output vẫn target clause_id.
* Explanation tiếng Việt, trung tính; không lời khuyên/hành động; không nhắc điều luật ngoài selected valid citations.
* Provider structured output theo `risk_output_v2`, không quote/span/Markdown.
