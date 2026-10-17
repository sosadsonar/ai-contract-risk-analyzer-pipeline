<!-- nguồn: SDD_AI_Labor_Contract_Risk_Analyzer_v0.1.md | mục: 9. LLM Integration Design | 967 ký tự | trước: 09_8-session-state-machine-va-dieu-phoi.md | sau: 11_10-legal-corpus-va-citation-validation.md -->

# 9. LLM Integration Design

## 9.1 Hai adapter sản phẩm

| Adapter | Input | Output | Quy tắc |
|---|---|---|---|
| Clause Classification | Batch (clause_id, masked clause) | clause_id + 1..3 clause_labels | Không quote/span/score tự khai. |
| Risk Analysis | Target clause + labels + role + legal candidates + optional related clause context | risk_labels, severity, explanation, citation_ids, evidence_status | Chỉ chọn citation trong candidates; severity null nếu thiếu evidence. |

## 9.2 LLM Client cross-cutting

* Provider cho demo/evaluation: Gemini Flash paid tier; model id bắt buộc cấu hình.
* Timeout mỗi call 30 giây; auto-retry tối đa 1 lần cho lỗi tạm thời.
* Structured output phải được validate; sai schema sau retry -> AI_OUTPUT_INVALID.
* Batch nhiều clause/call, mức batch và parallelism cấu hình theo D1.
* LLM call/token/estimated cost được ghi RunLog; log không chứa prompt chứa contract text.
* API key qua header, không hard-code, không log.
