import json

def get_mock_contract_analysis() -> dict:
    """Trả về dữ liệu chuẩn schema v2 để Backend và Risk AI dùng ngay lập tức."""
    mock_data = {
        "contract_id": "HD-001",
        "total_clauses": 2,
        "clauses": [
            {
                "clause_id": "clause_1",
                "clause_number": "Điều 3.1",
                "span": {"start_char": 1204, "end_char": 1389},
                "original_text": "Người lao động không được làm việc cho đối thủ cạnh tranh trong vòng 24 tháng...",
                "clause_type": ["CONFIDENTIALITY_IP", "TERMINATION"],
                "type_scores": {"CONFIDENTIALITY_IP": 0.95, "TERMINATION": 0.42},
                "max_content_risk_tier": "HIGH",
                "review_zone": "YELLOW",
                "review_reason": "TERMINATION score (0.42) < T_high(0.90) for HIGH tier"
            },
            {
                "clause_id": "clause_2",
                "clause_number": "Điều 4",
                "span": {"start_char": 1392, "end_char": 1470},
                "original_text": "Mức lương cơ bản là 10.000.000 VNĐ.",
                "clause_type": ["COMPENSATION"],
                "type_scores": {"COMPENSATION": 0.98},
                "max_content_risk_tier": "MEDIUM",
                "review_zone": "GREEN",
                "review_reason": None
            }
        ]
    }
    return mock_data