"""
File định nghĩa Taxonomy, Risk Tiers và Logic Routing dựa trên nguyên tắc "Worst-Case Risk".
"""

# Bản đồ ánh xạ Nhãn (Label) -> Tầng rủi ro (Risk Tier)
RISK_TAXONOMY_MAP = {
    # High-risk: Hậu quả pháp lý nghiêm trọng
    "CONFIDENTIALITY_IP": "HIGH",
    "TERMINATION": "HIGH",
    
    # Medium-risk: Ảnh hưởng quyền lợi kinh tế & thời gian làm việc
    "COMPENSATION": "MEDIUM",
    "WORKING_HOURS_LEAVE": "MEDIUM",
    "BENEFITS_INSURANCE": "MEDIUM",
    "DISPUTE_RESOLUTION": "MEDIUM",
    
    # Boilerplate: Thủ tục hành chính, ít rủi ro
    "JOB_DUTIES": "BOILERPLATE",
    "OTHER": "BOILERPLATE"
}

# Bảng ngưỡng Threshold risk-weighted
TIER_THRESHOLDS = {
    "HIGH":        {"t_low": 0.70, "t_high": 0.90},
    "MEDIUM":      {"t_low": 0.60, "t_high": 0.80},
    "BOILERPLATE": {"t_low": 0.50, "t_high": 0.65}
}

def compute_clause_routing(type_scores: dict[str, float]) -> dict:
    """
    Tính toán luồng xử lý (review_zone) dựa trên nguyên tắc Tấm khiên bi quan.
    """
    zone_priority = {"RED": 3, "YELLOW": 2, "GREEN": 1}
    current_worst_zone = "GREEN"
    reasons = []
    highest_tier = "BOILERPLATE"
    tier_rank = {"HIGH": 3, "MEDIUM": 2, "BOILERPLATE": 1}

    for label, score in type_scores.items():
        tier = RISK_TAXONOMY_MAP.get(label, "BOILERPLATE")
        
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