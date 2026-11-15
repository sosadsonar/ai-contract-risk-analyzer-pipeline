"""The M6 projection preserves source offsets without touching private data."""

import pytest
from app.session.m6_packet import review_rows_from_final_result


def test_review_packet_fields_and_offsets():
    source = "Điều khoản thử nghiệm."
    result = {
        "schema_version": "final_result_v1", "session_id": "dev-1",
        "role": "EMPLOYEE", "canonical_text": source,
        "risks": [{"risk_labels": ["UNILATERAL_CHANGE"], "severity": "MEDIUM",
                   "explanation": "Điều khoản chưa rõ.", "citation_ids": ["LAW:1"],
                   "quote": source, "start_char": 0, "end_char": len(source)}],
    }
    rows = review_rows_from_final_result(result)
    assert len(rows) == 1
    assert rows[0] == {"output_id": "dev-1::0001::UNILATERAL_CHANGE",
                       "role": "EMPLOYEE", "risk_label": "UNILATERAL_CHANGE",
                       "severity": "MEDIUM", "explanation": "Điều khoản chưa rõ.",
                       "citation_ids": ["LAW:1"], "quote": source,
                       "start_char": 0, "end_char": len(source)}
    result["risks"][0]["end_char"] -= 1
    with pytest.raises(ValueError, match="offset"):
        review_rows_from_final_result(result)
