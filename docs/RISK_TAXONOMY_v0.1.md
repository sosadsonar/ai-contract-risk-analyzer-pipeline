# Risk Taxonomy — Contract Risk Analyzer

## TL;DR
21 nhãn: `CONTRACT_TERM_TYPE`, `PROBATION`, `WAGE_AMOUNT_COMPONENTS`, `BONUS_BENEFITS`, `PAYMENT_TIMING_METHOD`, `WORKING_HOURS_OVERTIME`, 
`REST_AND_LEAVE`, `SOCIAL_INSURANCE`, `OSH_OBLIGATION`, `UNILATERAL_CHANGE`, `PENALTY_DEDUCTION_DAMAGES`, `DISCIPLINE_OBLIGATION`, `POST_EMPLOYMENT_RESTRICTION`, `DEPOSIT_DOCUMENT_HELD`, `DISCRIMINATION_PROTECTED_GROUPS`, `TRAINING_COMMITMENT`, `TERMINATION_GROUNDS_NOTICE`, `TERMINATION_SETTLEMENT`, `WAIVER_RIGHTS_DISPUTE`, `PERSONAL_DATA_PRIVACY`, `CONTRACT_FORM_RULES`

## Taxonomy

#### Note
- Một clause, nếu có rủi ro, trước hết được phân vào 1 trong 3 loại (risk types):
  - LEGAL_VIOLATION (LV)
  - UNFAVORABLE (UF)
  - AMBIGUOUS (AM)
- sau đó nó sẽ được gán risk label, gán severity dựa theo risk label đó + vai trò, tra trong bảng ở dưới.

#### Giải thích bảng Taxonomy
- risk_id: risk label
- Clause label chính: Clause được gán risk_label này khả năng cao thuộc về clause label nào (cross-reference)
- expression: Cơ sở để gắn nhãn risk (clause này có ý gì -> risk)
- EMPLOYEE (LV/UF/AM): severity theo risk type + vai trò **người lao động**.
- EMPLOYER (LV/UF/AM): severity theo risk type + vai trò **người sử dụng lao động**.
  - Severity LOW - MEDIUM - HIGH, nếu '-' nghĩa là loại đó không phải rủi ro cho vai trò này (ví dụ điều khoản có lợi hơn luật cho một bên thì không phải rủi ro của bên đó). 
  - Phần có dấu '-' để kiểm tra xem types và risk label được gán chuẩn không. Nếu 2 bước gán đó trả về kết quả có severity là - thì gắn cờ "need review" và coi là fail.
- Căn cứ: Căn cứ vào điều luật nào (chỉ là candidate/nói chung chung, CHUẨN/CHÍNH XÁC là phải truy xuất trong corpus theo nội dung clause).

#### Nội dung

| risk_id | Clause label chính | Gom từ (expression) | EMPLOYEE (LV/UF/AM) | EMPLOYER (LV/UF/AM) | Căn cứ (candidate) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| CONTRACT_TERM_TYPE | CONTRACT_TERM | Quá 36 tháng, ký nối tiếp quá số lần, hết hạn tự động | M / L / M | H / L / M | Điều 20 |
| PROBATION | CONTRACT_TERM | Thời gian, lương dưới 85%, phạt khi hủy | H / L / M | H / - / M | Điều 24 đến 27 |
| WAGE_AMOUNT_COMPONENTS | COMPENSATION_BENEFITS | Dưới tối thiểu vùng, lương gộp, tiền làm thêm giờ dưới luật, gross/net và thuế | H / M / M | H / M / M | NĐ 293/2025; Điều 98; Luật BHXH 2024 Điều 31; Luật Thuế TNCN 2025 |
| BONUS_BENEFITS | COMPENSATION_BENEFITS | Thưởng, phụ cấp do công ty toàn quyền, nhưng PHẢI công khai, nếu không -> LV; khoản chi cố định cam kết | L / M / M | H / M / L | Điều 104 |
| PAYMENT_TIMING_METHOD | COMPENSATION_BENEFITS | Kỳ hạn, phương thức, lương phụ thuộc điều kiện | H / M / M | H / - / M | Điều 94 đến 97 |
| WORKING_HOURS_OVERTIME | WORKING_TIME | Giờ làm việc thường, làm thêm bắt buộc, vượt trần | H / M / M | H / L / L | Điều 105, 107 |
| REST_AND_LEAVE | LEAVE | Nghỉ giữa ca, hằng tuần, phép năm, lễ, việc riêng, thanh toán phép chưa nghỉ | H / M / M | H / L / L | Điều 109 đến 115 |
| SOCIAL_INSURANCE | INSURANCE_SAFETY | Không đóng hoặc đóng thấp BHXH/BHYT/BHTN, người lao động chịu phần của công ty | H / - / M | H / - / M | Luật BHXH 2024; NĐ 158/2025, 274/2025, 283/2026 (Điều 43, 44); Luật Việc làm 2025, NĐ 374/2025 |
| OSH_OBLIGATION | INSURANCE_SAFETY | Đẩy chi phí bảo hộ, khám sức khỏe, tai nạn lao động sang người lao động | H / - / M | H / - / M | Luật ATVSLĐ 2015 |
| UNILATERAL_CHANGE | EMPLOYER_RIGHTS_OBLIGATIONS | Đơn phương đổi lương, công việc, địa điểm, ca; sửa hợp đồng; mô tả công việc để mở | H / M / M | M / L / L | Điều 21.1, 29, 33 |
| PENALTY_DEDUCTION_DAMAGES | EMPLOYEE_OBLIGATIONS_DISCIPLINE | Phạt tiền, khấu trừ lương, bồi thường vượt luật, phạt khi nghỉ việc | H / M / M | H / L / M | Điều 40, 101, 129 |
| DISCIPLINE_OBLIGATION | EMPLOYEE_OBLIGATIONS_DISCIPLINE | Hình thức và căn cứ kỷ luật, tiêu chí đánh giá, nghĩa vụ một chiều | H / M / M | H / L / M | Điều 36.1.a; mục kỷ luật |
| POST_EMPLOYMENT_RESTRICTION | EMPLOYEE_OBLIGATIONS_DISCIPLINE | Bảo mật, không cạnh tranh, chuyển giao sở hữu trí tuệ | M / M / M | - / L / M | Điều 5, 21.2; Luật SHTT |
| DEPOSIT_DOCUMENT_HELD | WORKING_CONDITIONS | Đặt cọc, ký quỹ, giữ bản chính giấy tờ | H / - / M | H / - / M | Điều 17 |
| DISCRIMINATION_PROTECTED_GROUPS | WORKING_CONDITIONS | Phân biệt đối xử, cấm kết hôn hoặc mang thai | H / - / M | H / - / M | Điều 8, 137, 138 |
| TRAINING_COMMITMENT | TRAINING | Hoàn trả chi phí đào tạo, thời gian cam kết, lợi dụng đào tạo để trục lợi | H / M / M | H / L / M | Điều 8, 61, 62 |
| TERMINATION_GROUNDS_NOTICE | TERMINATION | Căn cứ công ty được chấm dứt, báo trước hai bên, điều kiện để người lao động nghỉ | H / M / M | H / M / M | Điều 35, 36, 41 |
| TERMINATION_SETTLEMENT | TERMINATION | Trợ cấp thôi việc và mất việc, thanh toán cuối, trả giấy tờ, bàn giao | H / M / M | H / L / M | Điều 46 đến 48 |
| WAIVER_RIGHTS_DISPUTE | OTHER | buộc Employee từ bỏ quyền khiếu nại, khởi kiện; cấm/hạn chế tham gia công đoàn; loại trừ thẩm quyền | H / M / M | H / - / L | Điều 5, 49.1 |
| PERSONAL_DATA_PRIVACY | OTHER | Thu thập, chia sẻ, giám sát dữ liệu cá nhân | M / M / M | H / - / M | Luật BVDLCN 2025; NĐ 356/2025 |
| CONTRACT_FORM_RULES | OTHER | Hình thức hợp đồng, bản giữ, nội quy kèm theo, quyền giải thích của công ty | M / M / M | M / - / M | Điều 14, 118 đến 121; NĐ 337/2025 |

* Nếu chỉ ghi Điều #N _(không bộ luật đằng sau)_ ngầm định là trong Bộ luật Lao Động 2019