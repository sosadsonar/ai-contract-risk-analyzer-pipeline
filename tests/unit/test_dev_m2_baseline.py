"""Source-only Dev M2 rules on synthetic clauses."""

from app.risk.dev_m2_baseline import detect_dev_m2_risks

UNILATERAL = ("EMPLOYEE", "UNILATERAL_CHANGE", "AMBIGUOUS")


def test_open_ended_other_work_is_unilateral_change():
    text = "Người lao động phải thực hiện các công việc khác theo yêu cầu của Công ty."
    assert UNILATERAL in detect_dev_m2_risks(text)


def test_unbounded_company_assignment_is_unilateral_change():
    text = "Người lao động phải chấp nhận mọi sự điều động theo phân công của Ban Giám đốc."
    assert UNILATERAL in detect_dev_m2_risks(text)


def test_unilateral_pay_change_is_detected():
    text = "Công ty có quyền thay đổi mức lương của người lao động đơn phương."
    assert UNILATERAL in detect_dev_m2_risks(text)


def test_mutually_agreed_change_is_not_flagged():
    text = "Việc thay đổi công việc và địa điểm làm việc được hai bên thỏa thuận bằng văn bản."
    assert UNILATERAL not in detect_dev_m2_risks(text)


def test_ordinary_assignment_without_open_discretion_is_not_flagged():
    text = "Công ty phân công công việc phù hợp theo hợp đồng đã ký."
    assert UNILATERAL not in detect_dev_m2_risks(text)
