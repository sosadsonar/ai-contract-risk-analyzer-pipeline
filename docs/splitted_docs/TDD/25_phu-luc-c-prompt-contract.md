<!-- nguồn: TDD_AI_Labor_Contract_Risk_Analyzer_v0.2.md | mục: Phụ lục C. Prompt contract | 999 ký tự | trước: 24_phu-luc-b-env-example.md | sau: 26_phu-luc-d-checklist-truoc-khi-khoa-demo.md -->

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
* Thiếu căn cứ -> INSUFFICIENT_EVIDENCE, severity null, citations empty.
* related_clauses chỉ context cho điều kiện/phụ thuộc/mâu thuẫn; output vẫn target clause_id.
* Explanation tiếng Việt, trung tính; không lời khuyên/hành động; không nhắc điều luật ngoài selected valid citations.
* Provider structured output theo `risk_output_v2`, không quote/span/Markdown.
