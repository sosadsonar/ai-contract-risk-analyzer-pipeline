from app.risk.dev_injection_baseline import detect_dev_risks


def test_dev_rule_detects_employer_document_retention():
    assert ("EMPLOYER", "DEPOSIT_DOCUMENT_HELD") in detect_dev_risks(
        "Công ty giữ bản chính văn bằng của người lao động."
    )


def test_dev_rule_detects_employee_deposit():
    assert ("EMPLOYEE", "DEPOSIT_DOCUMENT_HELD") in detect_dev_risks(
        "Người lao động phải giao tiền đặt cọc khi nhận việc."
    )


def test_dev_rule_does_not_label_unrelated_clause():
    assert detect_dev_risks("Người lao động được nghỉ hằng năm theo quy định.") == ()
