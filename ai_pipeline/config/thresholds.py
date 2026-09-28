"""
File định nghĩa Taxonomy, Risk Tiers và Logic Routing dựa trên nguyên tắc "Worst-Case Risk".

Taxonomy = 12 nhãn của data repo (ai_pipeline/data/docs/clause_taxonomy_v02.md).
Đây là NGUỒN DUY NHẤT trong code: SYSTEM_PROMPT của LLM cũng được sinh ra từ
LABEL_DEFINITIONS bên dưới, nên đổi nhãn ở đây là prompt tự đổi theo.

⚠️ Tier (HIGH/MEDIUM/BOILERPLATE) là ĐỀ XUẤT của Người 1 khi chuyển từ 8 nhãn
sang 12 nhãn — Người 3 (Risk AI Lead) là người chốt cuối cùng. Xem
docs/CLAUSE_TAXONOMY.md mục 3 để biết lý do từng tier và những chỗ cần chốt.
"""

# Nhãn -> (định nghĩa ngắn cho LLM). Thứ tự = thứ tự hiển thị trong prompt.
LABEL_DEFINITIONS = {
    "JOB_INFO": "công việc, chức danh, bộ phận, địa điểm làm việc, nhiệm vụ và phạm vi công việc.",
    "CONTRACT_TERM": "loại và thời hạn hợp đồng lao động, ngày bắt đầu/kết thúc.",
    "COMPENSATION_BENEFITS": "lương, phụ cấp, thưởng, nâng lương, công tác phí và các chế độ/quyền lợi tài chính.",
    "WORKING_TIME": "giờ làm việc, lịch làm việc, ca làm, làm thêm giờ/tăng ca.",
    "LEAVE": "nghỉ hằng tuần, phép năm, nghỉ lễ/Tết, nghỉ bù.",
    "INSURANCE_SAFETY": "BHXH/BHYT/BHTN, an toàn và vệ sinh lao động.",
    "WORKING_CONDITIONS": "công cụ, thiết bị, phương tiện và điều kiện vật chất phục vụ công việc.",
    "TRAINING": "đào tạo, bồi dưỡng, cam kết sau đào tạo và hoàn trả chi phí đào tạo.",
    "EMPLOYEE_OBLIGATIONS_DISCIPLINE": (
        "nghĩa vụ, kỷ luật, trách nhiệm vật chất, bồi thường và nghĩa vụ thuế của người lao động "
        "(kể cả cam kết bảo mật/không cạnh tranh nếu có)."
    ),
    "EMPLOYER_RIGHTS_OBLIGATIONS": "quyền và nghĩa vụ quản lý, điều hành của người sử dụng lao động (điều chuyển, quản lý, yêu cầu bồi thường).",
    "TERMINATION": "căn cứ, điều kiện, thủ tục, thời hạn báo trước và hậu quả của việc chấm dứt hợp đồng lao động.",
    "OTHER": (
        "điều khoản thi hành, sửa đổi/phụ lục, số bản, hiệu lực và các nội dung không thuộc "
        "các nhóm trên (kể cả giải quyết tranh chấp nếu có)."
    ),
}

# Bản đồ ánh xạ Nhãn (Label) -> Tầng rủi ro (Risk Tier)
RISK_TAXONOMY_MAP = {
    # High-risk: hậu quả pháp lý/tài chính lớn, khó đảo ngược đối với người lao động
    "TERMINATION": "HIGH",
    "TRAINING": "HIGH",                          # cam kết sau đào tạo + hoàn trả chi phí
    "EMPLOYEE_OBLIGATIONS_DISCIPLINE": "HIGH",   # kỷ luật, bồi thường, (bảo mật/không cạnh tranh)

    # Medium-risk: ảnh hưởng quyền lợi kinh tế, thời gian làm việc, quyền quản lý
    "COMPENSATION_BENEFITS": "MEDIUM",
    "WORKING_TIME": "MEDIUM",
    "LEAVE": "MEDIUM",
    "INSURANCE_SAFETY": "MEDIUM",
    "EMPLOYER_RIGHTS_OBLIGATIONS": "MEDIUM",

    # Boilerplate: thông tin mô tả / thủ tục, ít rủi ro
    "JOB_INFO": "BOILERPLATE",
    "CONTRACT_TERM": "BOILERPLATE",
    "WORKING_CONDITIONS": "BOILERPLATE",
    "OTHER": "BOILERPLATE",
}

# Chặn lệch nhau giữa 2 bảng ngay khi import (thêm nhãn ở bảng này mà quên bảng kia -> lỗi luôn).
assert set(LABEL_DEFINITIONS) == set(RISK_TAXONOMY_MAP), (
    "LABEL_DEFINITIONS và RISK_TAXONOMY_MAP không cùng bộ nhãn: "
    f"{set(LABEL_DEFINITIONS) ^ set(RISK_TAXONOMY_MAP)}"
)

# Bảng ngưỡng Threshold risk-weighted
TIER_THRESHOLDS = {
    "HIGH":        {"t_low": 0.70, "t_high": 0.90},
    "MEDIUM":      {"t_low": 0.60, "t_high": 0.80},
    "BOILERPLATE": {"t_low": 0.50, "t_high": 0.65}
}

def compute_clause_routing(type_scores: dict[str, float]) -> dict:
    """
    Tính toán luồng xử lý (review_zone) dựa trên nguyên tắc Tấm khiên bi quan.

    Nhãn không nằm trong RISK_TAXONOMY_MAP sẽ báo lỗi (ValueError) thay vì âm thầm
    coi là BOILERPLATE — tránh trường hợp dùng nhãn cũ (taxonomy 8 nhãn) mà không ai biết.
    """
    zone_priority = {"RED": 3, "YELLOW": 2, "GREEN": 1}
    current_worst_zone = "GREEN"
    reasons = []
    highest_tier = "BOILERPLATE"
    tier_rank = {"HIGH": 3, "MEDIUM": 2, "BOILERPLATE": 1}

    for label, score in type_scores.items():
        if label not in RISK_TAXONOMY_MAP:
            raise ValueError(
                f"Nhãn '{label}' không có trong RISK_TAXONOMY_MAP. "
                f"Nhãn hợp lệ: {sorted(RISK_TAXONOMY_MAP)}"
            )
        tier = RISK_TAXONOMY_MAP[label]

        # Cập nhật tier rủi ro bản chất cao nhất của nội dung
        if tier_rank[tier] > tier_rank[highest_tier]:
            highest_tier = tier

        t_low = TIER_THRESHOLDS[tier]["t_low"]
        t_high = TIER_THRESHOLDS[tier]["t_high"]

        # Phân vùng hành vi kiểm duyệt
        if score < t_low:
            label_zone = "RED"
            reasons.append(f"{label} score ({score:.2f}) < T_low({t_low}) for {tier} tier")
        elif score < t_high:
            label_zone = "YELLOW"
            reasons.append(f"{label} score ({score:.2f}) < T_high({t_high}) for {tier} tier")
        else:
            label_zone = "GREEN"

        # Lấy vùng tệ nhất làm vùng routing chung cho cả clause
        if zone_priority[label_zone] > zone_priority[current_worst_zone]:
            current_worst_zone = label_zone

    return {
        "max_content_risk_tier": highest_tier,  # Mức độ rủi ro bản chất của nội dung clause
        "review_zone": current_worst_zone,      # Hành vi routing xử lý (RED/YELLOW/GREEN)
        "review_reason": "; ".join(reasons) if reasons else None
    }
