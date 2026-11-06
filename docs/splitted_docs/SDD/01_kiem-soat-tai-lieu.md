<!-- nguồn: SDD_AI_Labor_Contract_Risk_Analyzer_v0.2.md | mục: Kiểm soát tài liệu | 806 ký tự | trước: 00_system-design-document.md | sau: 02_1-muc-dich-va-nguyen-tac-thiet-ke.md -->

# Kiểm soát tài liệu

| Mục | Giá trị |
|---|---|
| Tên tài liệu | System Design Document - AI Labor Contract Risk Analyzer |
| Phiên bản | 0.2 - Draft |
| Nguồn yêu cầu | BRD 0.6 (draft) và SRS 1.5 |
| Thay đổi so với 0.1 | Đồng bộ với SRS 1.5: Risk adapter trả basis_type (severity do backend tra bảng taxonomy), related_clause_ids, hạ evidence_status, thêm component Context Resolver, Cleanup Scheduler, Taxonomy Validator, Severity Resolver, Advice Linter; quota lưu bền; E2E đếm mọi phiên; M1-M10, EV-11, tập D3 và P1; sơ đồ cần vẽ lại theo bộ sơ đồ master ở ARCHITECTURE.md |
| Phạm vi | Thiết kế tổng thể, component, data flow, graph, security, deployment và mapping yêu cầu |
| Không thuộc SDD | HTTP endpoint cụ thể, JSON Schema chi tiết, class/function, package/thư viện cụ thể, prompt chi tiết |
