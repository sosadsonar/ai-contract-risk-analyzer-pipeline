<!-- nguồn: RISK_TAXONOMY_v0.1.md | mục: Risk Taxonomy - Contract Risk Analyzer > TL;DR | 1281 ký tự | trước: 00_risk-taxonomy-contract-risk-analyzer.md | sau: 02_quy-trinh-gan-nhan-theo-vai-tro-cua-phien.md -->

## TL;DR

21 nhãn: `CONTRACT_TERM_TYPE`, `PROBATION`, `WAGE_AMOUNT_COMPONENTS`, `BONUS_BENEFITS`, `PAYMENT_TIMING_METHOD`, `WORKING_HOURS_OVERTIME`, `REST_AND_LEAVE`, `SOCIAL_INSURANCE`, `OSH_OBLIGATION`, `UNILATERAL_CHANGE`, `PENALTY_DEDUCTION_DAMAGES`, `DISCIPLINE_OBLIGATION`, `POST_EMPLOYMENT_RESTRICTION`, `DEPOSIT_DOCUMENT_HELD`, `DISCRIMINATION_PROTECTED_GROUPS`, `TRAINING_COMMITMENT`, `TERMINATION_GROUNDS_NOTICE`, `TERMINATION_SETTLEMENT`, `WAIVER_RIGHTS_DISPUTE`, `PERSONAL_DATA_PRIVACY`, `CONTRACT_FORM_RULES`

Version: `risk_taxonomy_v01`, rubric `severity_v01` (rubric chữ ở SRS 2.3). Nguồn duy nhất trong code: `backend/app/risk/taxonomy.py`. Test `tests/unit/test_risk_taxonomy.py` đọc bảng bên dưới và so với code (nhãn, thứ tự, severity), nên sửa bảng thì phải sửa code (và ngược lại). Cột `Clause label tham khảo` không có trong code và không đưa vào prompt.

Trạng thái: **FROZEN** tại MS-1 (25/10/2026). Phần đóng băng: danh sách 21 nhãn, thứ tự nhãn, bảng severity (hai cột EMPLOYEE và EMPLOYER), hai version ở trên. Đổi một trong các phần này phải tăng version, đổi hằng trong `tests/unit/test_risk_taxonomy_freeze.py` và báo cả nhóm. Các cột `Clause label tham khảo`, `Gom từ (expression)`, `Căn cứ (candidate)` chỉ để đọc: sửa được, không cần tăng version.
