"""Synthetic checks for a single-reviewer Dev calibration, never human M6 acceptance."""

import pytest

from scripts.evaluate_m6_dev_calibration import calibrate_rows, judge_candidate

VALID_IDS = {
    "BLLD2019:art17:cl1", "BLLD2019:art17:cl2", "BLLD2019:art17:cl3"
}


def _row(text, label, citation, explanation):
    return {"output_id": "synthetic-1", "document_id": "HDLD001",
            "masked_clause_text": text, "risk_label": label,
            "citation_candidate": citation, "explanation_candidate": explanation}


@pytest.mark.parametrize("row", [
    _row("Người lao động phải nộp bản gốc bằng tốt nghiệp để Công ty giữ.",
         "DEPOSIT_DOCUMENT_HELD", "BLLD2019:art17:cl1",
         "Dấu hiệu giữ giấy tờ gốc khi thực hiện hợp đồng."),
    _row("Người lao động phải đặt cọc tiền để bảo đảm làm việc.",
         "DEPOSIT_DOCUMENT_HELD", "BLLD2019:art17:cl2",
         "Dấu hiệu yêu cầu bảo đảm bằng tiền khi thực hiện hợp đồng."),
    _row("Người lao động chưa được nghỉ việc khi còn khoản nợ của Công ty.",
         "EMPLOYEE_OBLIGATIONS_DISCIPLINE", "BLLD2019:art17:cl3",
         "Dấu hiệu buộc tiếp tục làm việc để trả nợ."),
])
def test_distinct_legal_crosscheck_accepts_valid_article17_candidate(row):
    assert judge_candidate(row, VALID_IDS) == "DUNG"


def test_crosscheck_rejects_negated_retention():
    row = _row("Công ty không giữ bản gốc bằng tốt nghiệp của người lao động.",
               "DEPOSIT_DOCUMENT_HELD", "BLLD2019:art17:cl1",
               "Dấu hiệu giữ giấy tờ gốc khi thực hiện hợp đồng.")
    assert judge_candidate(row, VALID_IDS) == "SAI"


def test_crosscheck_marks_wrong_citation_or_advice_as_partial():
    row = _row("Người lao động phải đặt cọc tiền để bảo đảm làm việc.",
               "DEPOSIT_DOCUMENT_HELD", "BLLD2019:art17:cl1",
               "Dấu hiệu yêu cầu bảo đảm bằng tiền; người lao động nên sửa điều khoản.")
    assert judge_candidate(row, VALID_IDS) == "DUNG_MOT_PHAN"


def test_duplicate_human_b_is_explicitly_synthetic_and_not_acceptance():
    packet = [dict(_row("Người lao động phải đặt cọc tiền để bảo đảm làm việc.",
                        "DEPOSIT_DOCUMENT_HELD", "BLLD2019:art17:cl2",
                        "Dấu hiệu yêu cầu bảo đảm bằng tiền."), output_id=f"synthetic-{i}")
              for i in range(40)]
    draft = [{"output_id": f"synthetic-{i}", "human_a": "DUNG",
              "human_b": "", "human_adjudicated": "", "judge": ""}
             for i in range(40)]
    result = calibrate_rows(packet, draft, VALID_IDS)
    assert result["mode"] == "SINGLE_REVIEWER_APPROVED_DEV_CALIBRATION"
    assert result["judge_human_agreement"] == 1.0
    assert result["m6_threshold_met"] is True
    assert result["acceptance_scope_verified"] is False
    assert result["human_b_is_synthetic_copy"] is True
    assert result["human_a_b_kappa"] is None
