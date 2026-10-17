<!-- nguồn: SRS_AI_Labor_Contract_Risk_Analyzer_1_4.md | mục: SRS: AI Labor Contract Risk Analyzer (phiên bản 1.4) > 4. Yêu cầu dữ liệu | 5063 ký tự | trước: 05_3-yeu-cau-chuc-nang-phan-2-2.md | sau: 07_5-quy-tac-legal-retrieval-va-citation.md -->

## 4. Yêu cầu dữ liệu

### 4.1 Thực thể dữ liệu tối thiểu

| Thực thể | Trường tối thiểu | Quy tắc |
|---|---|---|
| Session | session_id, role, status, created_at, last_activity_at, manual_retry_count, filename, extraction_version, canonical_text, masked_text | session_id opaque, ngẫu nhiên; một vai trò và một hợp đồng; TTL 60 phút không hoạt động. Không có contract_id hay analysis_id. canonical_text là nguồn duy nhất cho quote, span, highlight; đổi extraction_version làm span cũ vô hiệu. |
| Clause | clause_id, original_text, start_char, end_char, clause_labels | clause_id duy nhất trong phiên. Masked clause không lưu riêng mà là masked_text[start_char:end_char]. Không lưu score không định nghĩa. Span phải thỏa invariant. |
| RiskResult | clause_id, role, risk_labels, risk_basis, severity, explanation, evidence_status, citation_ids, related_clause_ids? , các trường version (FR-29) | `risk_basis` do backend derive từ risk_labels và risk taxonomy, không do LLM tự khai. Severity thuộc HIGH/MEDIUM/LOW khi SUPPORTED; null khi INSUFFICIENT_EVIDENCE. `related_clause_ids` là optional; nếu có phải là subset context của target clause. |
| LegalProvision | citation_id, document_id, document_name, version, article, clause, point, parent_path, content, effective_from, effective_to | Là đơn vị retrievable và citable, thuộc closed corpus. citation_id sinh xác định từ document_id và đường dẫn điều, khoản, điểm. |
| RunLog | session_id, stage, started_at, duration_ms, calls, tokens, estimated_cost, error_code | Không chứa nội dung hợp đồng, canonical text hay dữ liệu cá nhân (NFR-SEC-05); phục vụ NFR-COST-01. |
| LegalEdge | from_citation_id, to_citation_id, edge_type, origin | Thuộc dữ liệu kho luật. origin chỉ AUTO hoặc MANUAL: PARENT_OF sinh từ parent_path là AUTO; REFERS_TO/GUIDES chỉ load runtime khi đã được xác minh và ghi MANUAL. Gợi ý tự động chưa xác minh không phải LegalEdge runtime. Hai đầu cạnh phải tồn tại. |
| ClauseEdge | from_clause_id, to_clause_id, edge_type | Thuộc dữ liệu phiên, xóa theo FR-23. Chỉ chứa ID. edge_type thuộc NEXT, PARENT_OF, REFERS_TO. |
| ContextResolutionTrace | target_clause_id, related_clause_ids, relations, graph_enabled | Chỉ dùng dev/evaluation/demo evidence; không chứa contract text hay PII. Product runtime không lưu bền vững; evaluation artifact có thể lưu vì dataset đã de-identify (EV-09). |

### 4.2 Invariant bắt buộc

* canonical_text[start_char:end_char] == original_text với mọi clause; start/end tính theo Unicode code point sau NFC.
* len(masked_text) == len(canonical_text); masked_text chỉ khác canonical_text ở các đoạn đã bị thay bằng placeholder cùng độ dài.
* Không ranh giới clause nào nằm bên trong một placeholder; clause spans có thứ tự và không chồng lấn.
* Response của LLM join bằng clause_id; AI không có thẩm quyền đối với quote và span.
* Span cũ không được dùng lại với canonical_text của extraction_version mới.
* Citation trả ra phải thuộc candidate list và closed legal corpus, đúng phiên bản hiệu lực tại ngày phân tích.
* Không tồn tại RiskResult không có clause_id; `risk_basis` phải khớp xác định với `risk_labels` trong risk taxonomy. `related_clause_ids` nếu có phải là subset context đã cung cấp cho target.
* Không tồn tại bảng ánh xạ từ placeholder sang giá trị gốc.
* Mọi LegalEdge trỏ tới hai citation_id tồn tại trong closed corpus; cạnh PARENT_OF không tạo vòng.
* Mở rộng qua Data Graph chỉ trả provision thuộc closed corpus và hiệu lực tại ngày phân tích; kết quả vẫn nằm trong candidate list mà LLM được chọn.
* Clause Graph chỉ chứa clause_id và loại cạnh; không chứa văn bản hợp đồng, không làm đổi span hay original_text. ContextResolutionTrace cũng không chứa contract text.

### 4.3 Dữ liệu vào và ra theo stage

Định nghĩa JSON Schema cho từng stage nằm ở TDD.

| Stage | Input tối thiểu | Output tối thiểu |
|---|---|---|
| Extraction | file, role | canonical_text, extraction_version |
| Scope precheck | canonical_text | chấp nhận, hoặc REJECTED kèm mã lỗi |
| PII Masking | canonical_text | masked_text cùng độ dài |
| Segmentation | canonical_text, masked_text | clause_id, original_text, start_char, end_char |
| Clause Graph build | clause_id, masked clause | ClauseEdge[] (from_clause_id, to_clause_id, edge_type) |
| Clause Classification | clause_id, masked clause, optional structural masked context; **không role** | clause_id, clause_labels[] |
| Legal Retrieval | clause_id, masked clause, clause_labels[], role, Data Graph | legal_candidates[] (citation_id, content, metadata), đã mở rộng qua Data Graph |
| Clause Graph context resolution | target clause_id, Clause Graph | related_clauses[] (clause_id, relation, masked text) + ContextResolutionTrace |
| Risk, Severity, Explanation | clause_id, masked clause, clause_labels[], role, legal_candidates[], optional related_clauses[] | clause_id, risk_labels[], severity, explanation, citation_ids[], evidence_status, optional related_clause_ids[] |
| Assembler | output AI và clause chuẩn | Kết quả cuối với original_text, span, `risk_basis` derive từ taxonomy và phân tích AI |
