<!-- nguồn: TDD_AI_Labor_Contract_Risk_Analyzer_v0.2.md | mục: 16. Export report | 946 ký tự | trước: 16_15-risk-analysis-citation-validation-va-assembly.md | sau: 18_17-logging-quota-rate-limit-retention-va-security.md -->

# 16. Export report

## 16.1 Report model

| Phần | Nội dung |
|---|---|
| Header | Tên hệ thống, ngày phân tích, vai trò, filename hiển thị, version summary. |
| Disclaimer | Nội dung BRD Phụ lục A + câu không kiểm tra missing-clause risk. |
| **Data notice** | Thông báo xử lý dữ liệu cá nhân theo BRD Phụ lục A/FR-25. |
| Summary | Số clause, số clause có risk, HIGH/MEDIUM/LOW, số INSUFFICIENT_EVIDENCE. |
| Risk section | Original clause quote, risk label + basis type, severity/chưa đủ căn cứ, explanation, citations. |
| Citation appendix | Tên văn bản, điều/khoản/điểm, version/effectivity. |
| Technical footer | schema/version pins; không PII masking internals. |

Quote dùng original_text. DOCX/PDF cùng ReportModel để không lệch nội dung. Export phải chứa **cả disclaimer và data notice**.

## 16.2 Lifecycle

Exporter tạo bytes in-memory nếu có thể; temp file chỉ khi renderer cần. Sau stream/error xóa ngay, không cache server-side.
