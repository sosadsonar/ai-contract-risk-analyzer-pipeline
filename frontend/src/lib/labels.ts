// Tên hiển thị tiếng Việt cho mã nhãn backend trả về. UI không bao giờ hiện mã thô như PROBATION.
// Nguồn mã: backend/app/risk/taxonomy.py (21 nhãn, risk_taxonomy_v02) và backend/app/clause/taxonomy.py (12 nhãn).
// Tên tiếng Việt là ĐỀ XUẤT của frontend (tài liệu chưa có tên hiển thị chính thức), cần nhóm duyệt.
// Nếu backend thêm nhãn mới mà file này chưa có, labelName() trả về chính mã đó (không vỡ UI).

export const RISK_LABEL_NAMES: Record<string, string> = {
  CONTRACT_TERM_TYPE: "Loại và thời hạn hợp đồng",
  PROBATION: "Thử việc",
  WAGE_AMOUNT_COMPONENTS: "Mức lương và các khoản cấu thành",
  BONUS_BENEFITS: "Thưởng và phụ cấp",
  PAYMENT_TIMING_METHOD: "Kỳ hạn và hình thức trả lương",
  WORKING_HOURS_OVERTIME: "Giờ làm việc và làm thêm",
  REST_AND_LEAVE: "Nghỉ ngơi và nghỉ phép",
  SOCIAL_INSURANCE: "Bảo hiểm xã hội",
  OSH_OBLIGATION: "An toàn, vệ sinh lao động",
  UNILATERAL_CHANGE: "Đơn phương thay đổi nội dung",
  PENALTY_DEDUCTION_DAMAGES: "Phạt, khấu trừ, bồi thường",
  DISCIPLINE_OBLIGATION: "Kỷ luật và nghĩa vụ",
  POST_EMPLOYMENT_RESTRICTION: "Ràng buộc sau khi nghỉ việc",
  DEPOSIT_DOCUMENT_HELD: "Đặt cọc, giữ giấy tờ",
  DISCRIMINATION_PROTECTED_GROUPS: "Phân biệt đối xử",
  TRAINING_COMMITMENT: "Cam kết đào tạo",
  TERMINATION_GROUNDS_NOTICE: "Căn cứ và thời hạn báo trước khi chấm dứt",
  TERMINATION_SETTLEMENT: "Trợ cấp và thanh toán khi chấm dứt",
  WAIVER_RIGHTS_DISPUTE: "Từ bỏ quyền, giải quyết tranh chấp",
  PERSONAL_DATA_PRIVACY: "Dữ liệu cá nhân",
  CONTRACT_FORM_RULES: "Hình thức hợp đồng, nội quy kèm theo",
};

export const CLAUSE_LABEL_NAMES: Record<string, string> = {
  JOB_INFO: "Công việc",
  CONTRACT_TERM: "Loại và thời hạn hợp đồng",
  COMPENSATION_BENEFITS: "Lương và phúc lợi",
  WORKING_TIME: "Thời giờ làm việc",
  LEAVE: "Nghỉ phép",
  INSURANCE_SAFETY: "Bảo hiểm, an toàn lao động",
  WORKING_CONDITIONS: "Điều kiện làm việc",
  TRAINING: "Đào tạo",
  EMPLOYEE_OBLIGATIONS_DISCIPLINE: "Nghĩa vụ và kỷ luật của người lao động",
  EMPLOYER_RIGHTS_OBLIGATIONS: "Quyền và nghĩa vụ của người sử dụng lao động",
  TERMINATION: "Chấm dứt hợp đồng",
  OTHER: "Khác",
};

export const BASIS_TYPE_NAMES: Record<string, string> = {
  LEGAL_VIOLATION: "Trái quy định pháp luật",
  UNFAVORABLE: "Bất lợi",
  AMBIGUOUS: "Mơ hồ",
};

export const SEVERITY_NAMES: Record<string, string> = { HIGH: "Cao", MEDIUM: "Trung bình", LOW: "Thấp" };

const ALL: Record<string, string> = { ...CLAUSE_LABEL_NAMES, ...RISK_LABEL_NAMES, ...BASIS_TYPE_NAMES, ...SEVERITY_NAMES };

/** Tên hiển thị của một mã; mã lạ thì trả lại nguyên mã. Lưu ý CONTRACT_TERM_TYPE (rủi ro) khác CONTRACT_TERM (clause). */
export function labelName(code: string): string {
  return ALL[code] ?? code;
}
