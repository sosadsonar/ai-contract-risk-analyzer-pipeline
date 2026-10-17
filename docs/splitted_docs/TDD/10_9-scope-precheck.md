<!-- nguồn: TDD_AI_Labor_Contract_Risk_Analyzer_v0.2.md | mục: 9. Scope Precheck | 1143 ký tự | trước: 09_8-document-processing-va-canonical-text.md | sau: 11_10-pii-masking.md -->

# 9. Scope Precheck

FR-06 dùng luật cục bộ, không LLM. Precheck match trên normalized copy và không sửa canonical text.

## 9.1 Rule set

| Nhóm tín hiệu | Ví dụ | Điểm |
|---|---|---|
| Strong title | “hợp đồng lao động”, “hợp đồng thử việc” **trong `SCOPE_TITLE_SCAN_CHARS` ký tự đầu** | +3 |
| Party terms | “người lao động” và “người sử dụng lao động”/“bên sử dụng lao động” | +2 nếu có cả hai |
| Employment content | lương, thời giờ, công việc/chức danh, thời hạn | +1 mỗi nhóm, max +3 |
| Structure | >=2 heading Điều/Khoản hoặc mục quyền/nghĩa vụ | +1 |
| Strong negative | hóa đơn, mua bán, thuê nhà, dịch vụ thuần túy và không có employment party terms | -3 |

`Strong title` chỉ được tính khi phrase nằm trong 1.000 code point đầu (config) hoặc vùng title được extractor đánh dấu; mention “hợp đồng lao động” sâu trong thân tài liệu không tự động ACCEPT.

Decision default: ACCEPT nếu có strong title + ít nhất một employment signal; hoặc tổng score >=4 và có ít nhất một party term. REJECT nếu score <4 hoặc strong negative chiếm ưu thế. Hợp đồng thử việc và phụ lục nằm cùng file được chấp nhận. Fixture dương/âm khóa trước MS-2.
