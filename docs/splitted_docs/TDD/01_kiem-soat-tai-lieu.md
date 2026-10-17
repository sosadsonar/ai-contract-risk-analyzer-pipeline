<!-- nguồn: TDD_AI_Labor_Contract_Risk_Analyzer_v0.2.md | mục: Kiểm soát tài liệu | 3029 ký tự | trước: 00_preamble.md | sau: 02_1-muc-dich-pham-vi-va-invariant-ky-thuat.md -->

# Kiểm soát tài liệu

| Mục | Giá trị |
|---|---|
| Tên tài liệu | Technical Design Document - AI Labor Contract Risk Analyzer |
| Phiên bản | 0.2 - Draft |
| Ngày | 12/10/2026 |
| Nguồn yêu cầu | BRD 0.5 (draft), SRS 1.3, SDD 0.1 |
| Phạm vi | API contract, JSON Schema, module/class, thuật toán local, graph, legal retrieval, LLM adapter, cấu hình, test và evaluation artifacts |
| Không thay đổi | Business scope, pipeline invariant, state semantics, privacy boundary, closed-corpus rule, chỉ số nghiệm thu trong BRD |
| Trạng thái | Draft kỹ thuật; các giá trị cấu hình ghi “tune trên D1” được phép đổi mà không đổi API/schema semantics |

## Thay đổi chính trong 0.2

Bản 0.2 rà soát lại TDD 0.1 theo BRD 0.5, SRS 1.3, SDD 0.1 và review kỹ thuật. Các thay đổi chính: thống nhất upload bất đồng bộ và trạng thái REJECTED; bổ sung basis type ở final view nhưng giữ `risk_labels` của SRS; sửa retry/processing lock; làm M8 graph on/off công bằng; khóa partition clause không chồng lấn; tăng kiểm tra PDF font cũ; sửa Clause Graph REFERS_TO; tối ưu payload/token; bổ sung frontend contract, fixture format, privacy/BL-1/annotation metrics; và khóa deployment một worker cho session store in-memory.

Các đề xuất đòi hỏi thay đổi SRS (ví dụ thêm trường `related_clause_ids` vào RiskResult) **không được tự ý đưa vào product schema**. TDD 0.2 dùng diagnostic/evaluation trace để chứng minh Clause Graph đã được dùng, đồng thời ghi mục cần backport SRS ở §21.

## Quy tắc ưu tiên nguồn

* BRD 0.5 là nguồn nghiệp vụ và Evaluation Plan. TDD không thay đổi phạm vi, business rule hay ngưỡng M1-M8/PII.
* SRS 1.3 là nguồn bắt buộc cho FR/NFR, entity tối thiểu, invariant, state và error code.
* SDD 0.1 là nguồn kiến trúc: modular monolith, session tạm thời, Data Graph như lớp mở rộng, Clause Graph như Context Resolver, hai LLM call bắt buộc.
* TDD chỉ khóa chi tiết còn mở ở SDD §16 và SRS OI-02..OI-09/OI-12. Nếu TDD mâu thuẫn BRD/SRS, BRD/SRS thắng và TDD phải sửa.

| Lưu ý trạng thái: BRD 0.5, SRS 1.3 và SDD 0.1 đều đang ở trạng thái draft/chờ duyệt ở một số quyết định. TDD này giữ nguyên các quyết định draft đó thay vì tự đổi phạm vi. |
|---|

## Mục lục logic

* 1. Mục đích, phạm vi và invariant kỹ thuật
* 2. Các quyết định kỹ thuật TDD
* 3. Stack triển khai và cấu trúc repository
* 4. Configuration, secret và startup
* 5. HTTP API Contract
* 6. Domain model và JSON Schema
* 7. Analysis Orchestrator, state machine và retry/resume
* 8. Document Processing và canonical text
* 9. Scope Precheck
* 10. PII Masking
* 11. Clause Segmentation
* 12. Clause Graph và Context Resolver
* 13. Clause Classification LLM
* 14. Legal Corpus, Baseline Retrieval và Data Graph
* 15. Risk Analysis, citation validation và assembly
* 16. Export report
* 17. Logging, quota, rate limit, retention và security
* 18. Evaluation Harness và gold format
* 19. Test strategy
* 20. Traceability và kế hoạch migration codebase
* 21. Open items / giới hạn đã biết
* Phụ lục A-E: schema mẫu, env, prompt contract, checklist và UI message catalog
