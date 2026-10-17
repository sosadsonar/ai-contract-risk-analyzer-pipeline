<!-- nguồn: SDD_AI_Labor_Contract_Risk_Analyzer_v0.1.md | mục: 7. Kiến trúc dữ liệu và lưu trữ | 1711 ký tự | trước: 07_6-thiet-ke-clause-graph.md | sau: 09_8-session-state-machine-va-dieu-phoi.md -->

# 7. Kiến trúc dữ liệu và lưu trữ

## 7.1 Phân loại dữ liệu

| Loại dữ liệu | Ví dụ | Lưu trữ | Vòng đời |
|---|---|---|---|
| Session content | File gốc, canonical_text, masked_text, clauses, RiskResult, Clause Graph | Memory / temp storage | Xóa khi End Session hoặc 60 phút inactivity; mất khi restart. |
| Legal knowledge | LegalProvision, LegalEdge, taxonomy artifacts | Versioned corpus artifacts / index | Persistent, cập nhật ngoài source code. |
| Operational metadata | RunLog, token/cost, quota counter, error metadata | Metadata-only store/log | Có thể persistent; không chứa contract content/PII. |
| Evaluation data | D1/D2/T1/T2 đã de-identify, gold, metrics output | Evaluation workspace | Ngoài session runtime; theo BRD 8. |

## 7.2 Session aggregate

Session
- session_id
- role
- status / current_stage
- created_at / last_activity_at
- manual_retry_count
- filename
- extraction_version
- canonical_text
- masked_text
- clauses[]
- clause_graph
- clause_classification_outputs
- legal_candidates
- risk_results[]
- version_pins
- last_error

Đây là aggregate runtime ở mức thiết kế; exact schema/class được định nghĩa trong TDD. Không có contract_id hoặc analysis_id theo DEC-03.

## 7.3 Invariant dữ liệu

* canonical_text[start_char:end_char] == original_text với mọi clause.
* len(masked_text) == len(canonical_text).
* Không clause boundary nào nằm giữa một placeholder.
* Không có bảng mapping placeholder -> giá trị gốc.
* Mọi RiskResult có clause_id.
* Severity null khi evidence_status = INSUFFICIENT_EVIDENCE.
* Citation phải thuộc final candidate list, closed corpus và hiệu lực ở analysis date.
* Clause Graph chỉ chứa clause_id và edge_type; Data Graph không chứa contract data.
