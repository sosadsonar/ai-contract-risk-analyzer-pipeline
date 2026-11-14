from app.risk.dev_injection_baseline import detect_dev_risks
from app.risk.dev_injection_candidate import _propositions, detect_dev_risks_candidate

from ai_pipeline.evaluation.metrics.risk_classification import map_dev_candidate_to_risk_labels


def test_m5_candidate_label_bridge_is_explicit_and_does_not_change_detector():
    source = "Người lao động phải làm việc đến khi thanh toán hết khoản nợ cho Công ty."
    before = detect_dev_risks_candidate(source)
    mapped = map_dev_candidate_to_risk_labels(before)
    assert before == detect_dev_risks_candidate(source)
    assert mapped == tuple((role, "DISCIPLINE_OBLIGATION") for role in ("EMPLOYEE", "EMPLOYER"))
    assert map_dev_candidate_to_risk_labels((("EMPLOYEE", "DEPOSIT_DOCUMENT_HELD"),)) == (
        ("EMPLOYEE", "DEPOSIT_DOCUMENT_HELD"),)


def test_dev_candidate_preserves_baseline_and_exposes_both_source_supported_roles():
    text = "Công ty giữ bản chính giấy tờ; người lao động phải giao giấy tờ cho Công ty."
    baseline = set(detect_dev_risks(text))
    candidate = set(detect_dev_risks_candidate(text))
    assert baseline <= candidate
    assert ("EMPLOYER", "DEPOSIT_DOCUMENT_HELD") in candidate
    assert ("EMPLOYEE", "DEPOSIT_DOCUMENT_HELD") in candidate


def test_security_money_kept_at_employer_exposes_both_roles():
    text = "Người lao động phải duy trì khoản tiền bảo đảm tại Công ty trong thời hạn hợp đồng."
    candidate = set(detect_dev_risks_candidate(text))
    assert ("EMPLOYEE", "DEPOSIT_DOCUMENT_HELD") in candidate
    assert ("EMPLOYER", "DEPOSIT_DOCUMENT_HELD") in candidate


def test_explicit_no_retention_is_not_document_risk():
    text = "Công ty không giữ bản chính giấy tờ của người lao động trong thời hạn hợp đồng."
    assert not any(label == "DEPOSIT_DOCUMENT_HELD" for _, label in detect_dev_risks_candidate(text))


def test_generic_article_17_security_and_debt_use_both_roles():
    examples = (
        ("Nhân viên giao tài sản cho Công ty làm bảo đảm thực hiện hợp đồng.", "DEPOSIT_DOCUMENT_HELD"),
        ("Thời hạn làm việc được kéo dài cho đến khi nhân viên thanh toán hết khoản nợ với Công ty.",
         "EMPLOYEE_OBLIGATIONS_DISCIPLINE"),
        ("Nhân viên phải thực hiện công việc theo hợp đồng nhằm trả khoản nợ với Công ty.",
         "EMPLOYEE_OBLIGATIONS_DISCIPLINE"),
    )
    for text, label in examples:
        assert set(detect_dev_risks_candidate(text)) >= {
            ("EMPLOYEE", label), ("EMPLOYER", label)
        }


def test_article_17_negative_guards():
    examples = (
        "Công ty không yêu cầu người lao động đặt cọc để thực hiện hợp đồng.",
        "Công ty không giữ bản gốc căn cước của nhân viên.",
        "Công ty không buộc người lao động làm việc để trả nợ.",
        "Người lao động phải làm việc để trả khoản nợ cho ngân hàng.",
    )
    for text in examples:
        assert detect_dev_risks_candidate(text) == ()


def test_original_document_vocabulary_and_copy_guard():
    for term in ("căn cước", "CCCD", "CMND", "hộ chiếu", "bằng tốt nghiệp", "chứng chỉ"):
        text = f"Công ty giữ {term} của người lao động đến khi hết hợp đồng."
        assert ("EMPLOYER", "DEPOSIT_DOCUMENT_HELD") in detect_dev_risks_candidate(text)
    assert detect_dev_risks_candidate("Công ty lưu giữ bản sao hộ chiếu để hoàn thiện hồ sơ.") == ()


def test_negation_in_other_clause_does_not_cancel_document_risk():
    text = "Nếu không tiếp tục hợp tác, Công ty giữ bản gốc căn cước của nhân viên."
    assert ("EMPLOYEE", "DEPOSIT_DOCUMENT_HELD") in detect_dev_risks_candidate(text)
    text = "Công ty không giữ bản sao hồ sơ; Công ty giữ bản chính văn bằng đến khi hết hợp đồng."
    assert ("EMPLOYER", "DEPOSIT_DOCUMENT_HELD") in detect_dev_risks_candidate(text)


def test_debt_and_security_labels_can_coexist_without_overwrite():
    text = ("Nhân viên phải đặt cọc tiền bảo đảm tại Công ty và tiếp tục làm việc "
            "đến khi thanh toán hết khoản nợ với Công ty.")
    labels = {label for _, label in detect_dev_risks_candidate(text)}
    assert labels == {"DEPOSIT_DOCUMENT_HELD", "EMPLOYEE_OBLIGATIONS_DISCIPLINE"}


def test_debt_work_without_named_employer_still_has_both_roles():
    text = "Người lao động chưa được nghỉ việc trước khi hoàn trả khoản nợ phát sinh khi nhận việc."
    assert set(detect_dev_risks_candidate(text)) >= {
        ("EMPLOYEE", "EMPLOYEE_OBLIGATIONS_DISCIPLINE"),
        ("EMPLOYER", "EMPLOYEE_OBLIGATIONS_DISCIPLINE"),
    }


def test_article17_additional_source_vocabulary():
    examples = (
        ("Nhân viên nộp giấy phép lái xe cho Công ty, nhận lại sau khi chấm dứt hợp đồng.",
         "DEPOSIT_DOCUMENT_HELD"),
        ("Công ty yêu cầu mở tài khoản phong tỏa để bảo đảm thực hiện hợp đồng lao động.",
         "DEPOSIT_DOCUMENT_HELD"),
        ("Người lao động phải tiếp tục làm việc để hoàn trả khoản tiền đã nhận ứng trước.",
         "EMPLOYEE_OBLIGATIONS_DISCIPLINE"),
    )
    for text, label in examples:
        assert ("EMPLOYEE", label) in detect_dev_risks_candidate(text)


def test_restricted_rights_are_not_treated_as_negated_employer_action():
    assert ("EMPLOYEE", "EMPLOYEE_OBLIGATIONS_DISCIPLINE") in detect_dev_risks_candidate(
        "Người lao động không được nghỉ việc khi chưa hoàn trả chi phí đào tạo cho Công ty."
    )
    assert ("EMPLOYEE", "DEPOSIT_DOCUMENT_HELD") in detect_dev_risks_candidate(
        "Nhân viên không được nhận lại hộ chiếu do Công ty giữ đến khi chấm dứt hợp đồng."
    )


def test_direct_security_still_honors_explicit_negation():
    assert detect_dev_risks_candidate(
        "Công ty không yêu cầu người lao động đặt cọc để thực hiện hợp đồng."
    ) == ()


def test_copy_only_proposition_does_not_cancel_later_original_or_deposit():
    text = ("Nhân viên nộp bản sao chứng chỉ để lập hồ sơ. "
            "Công ty giữ bản chính văn bằng đến khi chấm dứt hợp đồng.")
    assert ("EMPLOYEE", "DEPOSIT_DOCUMENT_HELD") in detect_dev_risks_candidate(text)
    text = "Nhân viên nộp bản sao chứng chỉ; phải đặt cọc tiền khi nhận việc tại Công ty."
    assert ("EMPLOYER", "DEPOSIT_DOCUMENT_HELD") in detect_dev_risks_candidate(text)


def test_statutory_proposition_guards_do_not_label_lawful_deductions_or_training_alone():
    assert detect_dev_risks_candidate(
        "Công ty khấu trừ tiền lương để đóng BHXH hàng tháng."
    ) == ()


def test_full_document_names_and_article17_vs_article62():
    text = "Công ty giữ chứng minh thư của nhân viên làm tin trong thời gian làm việc."
    assert ("EMPLOYEE", "DEPOSIT_DOCUMENT_HELD") in detect_dev_risks_candidate(text)
    assert detect_dev_risks_candidate(
        "Nhân viên chỉ xuất trình chứng minh thư để đối chiếu khi nhận việc."
    ) == ()
    assert detect_dev_risks_candidate(
        "Người lao động cam kết làm việc cho Công ty 24 tháng sau khóa đào tạo; "
        "nếu nghỉ sớm thì hoàn trả chi phí đào tạo."
    ) == ()


def test_upfront_security_and_forced_repayment_are_distinct():
    security = "Nhân viên phải nộp trước khoản tiền để bảo đảm cam kết làm việc với Công ty."
    forced = "Người lao động buộc làm việc để trừ dần khoản nợ tạm ứng cho Công ty."
    assert ("EMPLOYER", "DEPOSIT_DOCUMENT_HELD") in detect_dev_risks_candidate(security)
    assert ("EMPLOYEE", "EMPLOYEE_OBLIGATIONS_DISCIPLINE") in detect_dev_risks_candidate(forced)
    assert detect_dev_risks_candidate(
        "Nhân viên cam kết làm việc sau đào tạo và hoàn trả chi phí đào tạo theo hợp đồng đào tạo."
    ) == ()


def test_money_periods_and_article_numbers_do_not_split_proposition():
    parts = _propositions("Điều 3. Người lao động phải nộp 5.000.000 đồng để cam kết thực hiện hợp đồng.")
    assert any("5.000.000" in part for part in parts)
    assert ("EMPLOYER", "DEPOSIT_DOCUMENT_HELD") in detect_dev_risks_candidate(
        "Người lao động phải nộp 5.000.000 đồng để cam kết thực hiện hợp đồng."
    )


def test_adjacent_propositions_combine_document_and_retention_evidence():
    text = ("Khi vào làm việc, người lao động phải giao nộp bằng tốt nghiệp đại học. "
            "Công ty sẽ lưu giữ văn bằng này trong suốt thời gian làm việc.")
    assert ("EMPLOYEE", "DEPOSIT_DOCUMENT_HELD") in detect_dev_risks_candidate(text)
