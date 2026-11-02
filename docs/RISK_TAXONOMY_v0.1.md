# Risk Taxonomy - Contract Risk Analyzer

## TL;DR
21 nhãn: `CONTRACT_TERM_TYPE`, `PROBATION`, `WAGE_AMOUNT_COMPONENTS`, `BONUS_BENEFITS`, `PAYMENT_TIMING_METHOD`, `WORKING_HOURS_OVERTIME`, `REST_AND_LEAVE`, `SOCIAL_INSURANCE`, `OSH_OBLIGATION`, `UNILATERAL_CHANGE`, `PENALTY_DEDUCTION_DAMAGES`, `DISCIPLINE_OBLIGATION`, `POST_EMPLOYMENT_RESTRICTION`, `DEPOSIT_DOCUMENT_HELD`, `DISCRIMINATION_PROTECTED_GROUPS`, `TRAINING_COMMITMENT`, `TERMINATION_GROUNDS_NOTICE`, `TERMINATION_SETTLEMENT`, `WAIVER_RIGHTS_DISPUTE`, `PERSONAL_DATA_PRIVACY`, `CONTRACT_FORM_RULES`

Version: `risk_taxonomy_v01`, rubric `severity_v01` (rubric chữ ở SRS 2.3). Nguồn duy nhất trong code: `backend/app/risk/taxonomy.py`. Test `tests/unit/test_risk_taxonomy.py` đọc bảng bên dưới và so với code (nhãn, thứ tự, severity), nên sửa bảng thì phải sửa code (và ngược lại). Cột `Clause label tham khảo` không có trong code và không đưa vào prompt.

Trạng thái: **FROZEN** tại MS-1 (25/10/2026). Phần đóng băng: danh sách 21 nhãn, thứ tự nhãn, bảng severity (hai cột EMPLOYEE và EMPLOYER), hai version ở trên. Đổi một trong các phần này phải tăng version, đổi hằng trong `tests/unit/test_risk_taxonomy_freeze.py` và báo cả nhóm. Các cột `Clause label tham khảo`, `Gom từ (expression)`, `Căn cứ (candidate)` chỉ để đọc: sửa được, không cần tăng version.`

## Quy trình gán nhãn (theo vai trò của phiên)
1. **basis_type**: một giá trị cho cả clause (LLM trả).
   - `LEGAL_VIOLATION` (LV): trái quy định cấm hoặc bắt buộc, hoặc vượt ngưỡng pháp luật rõ ràng trong kho luật.
   - `UNFAVORABLE` (UF): không trái luật nhưng bất lợi đáng kể cho vai trò đang phân tích.
   - `AMBIGUOUS` (AM): câu chữ mơ hồ, thiếu điều kiện hoặc mức cụ thể, có thể dẫn đến tranh chấp.
   - Nếu thỏa nhiều loại, ưu tiên LV, rồi UF, rồi AM.
2. **risk_labels**: 1 đến 3 nhãn trong bảng. Clause thường chỉ có một ý chính nên thường một nhãn.
3. **severity**: backend tra bảng theo (nhãn, basis_type, vai trò), LLM không trả severity. Nhiều nhãn thì lấy mức cao nhất. Severity phụ thuộc cả risk_basis, không chỉ nhãn và vai trò.
4. Nếu `evidence_status = INSUFFICIENT_EVIDENCE` thì severity trong kết quả là `null` bất kể bảng (SRS 2.3).

Lưu ý: basis_type là phán đoán về nội dung clause (trái luật, bất lợi hay mơ hồ), không phải hàm của nhãn. Vì vậy chỉ có thể tra xuôi (basis thành severity), không tra ngược severity hay nhãn về basis được.

## Cách đọc bảng
- `risk_id`: nhãn rủi ro.
- `Clause label tham khảo`: clause thường mang nhãn clause này (cross-reference). Chỉ để người đọc; không có trong code, không đưa vào prompt, không dùng để lọc hay giới hạn nhãn rủi ro. LLM tự phán đoán nhãn rủi ro.
- `Gom từ (expression)`: dấu hiệu trong clause dẫn đến nhãn này.
- `EMPLOYEE` / `EMPLOYER`: severity theo thứ tự `LV / UF / AM` của vai trò đó. `H` = HIGH, `M` = MEDIUM, `L` = LOW.
- `-`: tổ hợp đó KHÔNG phải rủi ro của vai trò này (ví dụ điều khoản có lợi hơn luật cho một bên thì không phải rủi ro của bên đó, BRD 3.2).
- `Căn cứ (candidate)`: điều luật có thể liên quan, chỉ là gợi ý. Căn cứ chính xác phải truy xuất trong corpus theo nội dung clause; LLM chỉ được trích citation nằm trong candidate của clause.

## Xử lý khi gặp ô `-`
Nếu bước 1 và 2 cho ra (nhãn, basis_type, vai trò) rơi vào `-` thì coi là gán sai: gắn cờ `need_review`, nhãn đó bị gỡ. Hết nhãn thì clause không xuất ra sản phẩm (không phải rủi ro của vai trò này) và được tính là fail khi chấm nhãn. Assembler (`backend/app/integrations/risk_assembler.py`) làm việc này, rồi dựng `risk_basis = [{label, basis_type}]` cho response sản phẩm và ghi vào `diagnostics`, không đưa vào response sản phẩm.

## Bảng

| risk_id | Clause label tham khảo | Gom từ (expression) | EMPLOYEE (LV/UF/AM) | EMPLOYER (LV/UF/AM) | Căn cứ (candidate) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| CONTRACT_TERM_TYPE | CONTRACT_TERM | Quá 36 tháng, ký nối tiếp quá số lần, hết hạn tự động | M / L / M | H / L / M | Điều 20 |
| PROBATION | CONTRACT_TERM | Thời gian, lương dưới 85%, phạt khi hủy | H / L / M | H / - / M | Điều 24 đến 27 |
| WAGE_AMOUNT_COMPONENTS | COMPENSATION_BENEFITS | Dưới tối thiểu vùng, lương gộp, tiền làm thêm giờ dưới luật, gross/net và thuế | H / M / M | H / M / M | NĐ 293/2025; Điều 98; Luật BHXH 2024 Điều 31; Luật Thuế TNCN 2025 |
| BONUS_BENEFITS | COMPENSATION_BENEFITS | Thưởng, phụ cấp do công ty toàn quyền, nhưng PHẢI công khai, nếu không -> LV; khoản chi cố định cam kết | M / M / M | H / M / L | Điều 104 |
| PAYMENT_TIMING_METHOD | COMPENSATION_BENEFITS | Kỳ hạn, phương thức, lương phụ thuộc điều kiện | H / M / M | H / - / M | Điều 94 đến 97 |
| WORKING_HOURS_OVERTIME | WORKING_TIME | Giờ làm việc thường, làm thêm bắt buộc, vượt trần | H / M / M | H / L / L | Điều 105, 107 |
| REST_AND_LEAVE | LEAVE | Nghỉ giữa ca, hằng tuần, phép năm, lễ, việc riêng, thanh toán phép chưa nghỉ | H / M / M | H / L / L | Điều 109 đến 115 |
| SOCIAL_INSURANCE | INSURANCE_SAFETY | Không đóng hoặc đóng thấp BHXH/BHYT/BHTN, người lao động chịu phần của công ty | H / - / M | H / - / M | Luật BHXH 2024; NĐ 158/2025, 274/2025, 283/2026 (Điều 43, 44); Luật Việc làm 2025, NĐ 374/2025 |
| OSH_OBLIGATION | INSURANCE_SAFETY | Đẩy chi phí bảo hộ, khám sức khỏe, tai nạn lao động sang người lao động | H / - / M | H / - / M | Luật ATVSLĐ 2015 |
| UNILATERAL_CHANGE | EMPLOYER_RIGHTS_OBLIGATIONS, JOB_INFO | Đơn phương đổi lương, công việc, địa điểm, ca; sửa hợp đồng; mô tả công việc để mở | H / M / M | M / L / L | Điều 21.1, 29, 33 |
| PENALTY_DEDUCTION_DAMAGES | EMPLOYEE_OBLIGATIONS_DISCIPLINE | Phạt tiền, khấu trừ lương, bồi thường vượt luật, phạt khi nghỉ việc | H / M / M | H / L / M | Điều 40, 101, 129 |
| DISCIPLINE_OBLIGATION | EMPLOYEE_OBLIGATIONS_DISCIPLINE | Hình thức và căn cứ kỷ luật, tiêu chí đánh giá, nghĩa vụ một chiều | H / M / M | H / L / M | Điều 36.1.a; mục kỷ luật |
| POST_EMPLOYMENT_RESTRICTION | EMPLOYEE_OBLIGATIONS_DISCIPLINE | Bảo mật, không cạnh tranh, chuyển giao sở hữu trí tuệ | M / M / M | M / L / M | Điều 5, 21.2; Luật SHTT |
| DEPOSIT_DOCUMENT_HELD | WORKING_CONDITIONS | Đặt cọc, ký quỹ, giữ bản chính giấy tờ | H / - / M | H / - / M | Điều 17 |
| DISCRIMINATION_PROTECTED_GROUPS | WORKING_CONDITIONS | Phân biệt đối xử, cấm kết hôn hoặc mang thai | H / - / M | H / - / M | Điều 8, 137, 138 |
| TRAINING_COMMITMENT | TRAINING | Hoàn trả chi phí đào tạo, thời gian cam kết, lợi dụng đào tạo để trục lợi | H / M / M | H / L / M | Điều 8, 61, 62 |
| TERMINATION_GROUNDS_NOTICE | TERMINATION | Căn cứ công ty được chấm dứt, báo trước hai bên, điều kiện để người lao động nghỉ | H / M / M | H / M / M | Điều 35, 36, 41 |
| TERMINATION_SETTLEMENT | TERMINATION | Trợ cấp thôi việc và mất việc, thanh toán cuối, trả giấy tờ, bàn giao | H / M / M | H / L / M | Điều 46 đến 48 |
| WAIVER_RIGHTS_DISPUTE | OTHER | buộc Employee từ bỏ quyền khiếu nại, khởi kiện; cấm/hạn chế tham gia công đoàn; loại trừ thẩm quyền | H / M / M | H / - / L | Điều 5, 49.1 |
| PERSONAL_DATA_PRIVACY | OTHER | Thu thập, chia sẻ, giám sát dữ liệu cá nhân | M / M / M | H / - / M | Luật BVDLCN 2025; NĐ 356/2025 |
| CONTRACT_FORM_RULES | OTHER | Hình thức hợp đồng, bản giữ, nội quy kèm theo, quyền giải thích của công ty | M / M / M | M / - / M | Điều 14, 118 đến 121; NĐ 337/2025 |

* Nếu chỉ ghi Điều #N _(không bộ luật đằng sau)_ ngầm định là trong Bộ luật Lao Động 2019

## Giới hạn đã biết
- `basis_type` là một giá trị cho cả clause. Clause có nhiều nhãn rủi ro dùng chung một basis, nên `risk_basis` của từng nhãn là cùng một giá trị và có thể không phản ánh đúng từng nhãn. Severity của clause là mức cao nhất trong các nhãn còn hợp lệ cho vai trò.
- Khi một clause thỏa nhiều basis, thứ tự ưu tiên là LV, rồi UF, rồi AM (quy tắc đã chốt, SRS/TDD chưa nêu). Prompt `risk_v1` phải nêu đúng thứ tự này. Nhãn rơi vào ô `-` của basis đã chọn bị gỡ theo FR-13; số nhãn bị gỡ (`labels_dropped`, `need_review` trong diagnostics) cần đếm trên D1 ở T6.
- Rubric severity ở SRS 2.3 chỉ là hướng dẫn đọc. Severity thật do bảng này quyết định; khi rubric và bảng khác nhau thì bảng thắng.
- Các ô LEGAL_VIOLATION không phải HIGH (8 ô, đều MEDIUM). EMPLOYEE: CONTRACT_TERM_TYPE, BONUS_BENEFITS, POST_EMPLOYMENT_RESTRICTION, PERSONAL_DATA_PRIVACY, CONTRACT_FORM_RULES. EMPLOYER: UNILATERAL_CHANGE, POST_EMPLOYMENT_RESTRICTION, CONTRACT_FORM_RULES.
- Các ô AMBIGUOUS mức LOW (5 ô, đều EMPLOYER): BONUS_BENEFITS, WORKING_HOURS_OVERTIME, REST_AND_LEAVE, UNILATERAL_CHANGE, WAIVER_RIGHTS_DISPUTE.
