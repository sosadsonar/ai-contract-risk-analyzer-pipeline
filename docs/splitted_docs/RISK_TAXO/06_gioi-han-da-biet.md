<!-- nguồn: RISK_TAXONOMY_v0.1.md | mục: Risk Taxonomy - Contract Risk Analyzer > Giới hạn đã biết | 1112 ký tự | trước: 05_bang.md | sau: - -->

## Giới hạn đã biết

- `basis_type` là một giá trị cho cả clause. Clause có nhiều nhãn rủi ro dùng chung một basis, nên `risk_basis` của từng nhãn là cùng một giá trị và có thể không phản ánh đúng từng nhãn. Severity của clause là mức cao nhất trong các nhãn còn hợp lệ cho vai trò.
- Khi một clause thỏa nhiều basis, thứ tự ưu tiên là LV, rồi UF, rồi AM (quy tắc đã chốt, SRS/TDD chưa nêu). Prompt `risk_v1` phải nêu đúng thứ tự này. Nhãn rơi vào ô `-` của basis đã chọn bị gỡ theo FR-13; số nhãn bị gỡ (`labels_dropped`, `need_review` trong diagnostics) cần đếm trên D1 ở T6.
- Rubric severity ở SRS 2.3 chỉ là hướng dẫn đọc. Severity thật do bảng này quyết định; khi rubric và bảng khác nhau thì bảng thắng.
- Các ô LEGAL_VIOLATION không phải HIGH (8 ô, đều MEDIUM). EMPLOYEE: CONTRACT_TERM_TYPE, BONUS_BENEFITS, POST_EMPLOYMENT_RESTRICTION, PERSONAL_DATA_PRIVACY, CONTRACT_FORM_RULES. EMPLOYER: UNILATERAL_CHANGE, POST_EMPLOYMENT_RESTRICTION, CONTRACT_FORM_RULES.
- Các ô AMBIGUOUS mức LOW (5 ô, đều EMPLOYER): BONUS_BENEFITS, WORKING_HOURS_OVERTIME, REST_AND_LEAVE, UNILATERAL_CHANGE, WAIVER_RIGHTS_DISPUTE.
