"""Source-only Dev M2 rules on synthetic clauses."""

from app.risk.dev_m2_baseline import detect_dev_m2_risks

UNILATERAL = ("EMPLOYEE", "UNILATERAL_CHANGE", "AMBIGUOUS")


def test_open_ended_other_work_is_unilateral_change():
    text = "Người lao động phải thực hiện các công việc khác theo yêu cầu của Công ty."
    assert UNILATERAL in detect_dev_m2_risks(text)


def test_unbounded_company_assignment_is_unilateral_change():
    text = "Người lao động phải chấp nhận mọi sự điều động theo phân công của Ban Giám đốc."
    assert UNILATERAL in detect_dev_m2_risks(text)


def test_unbounded_assignment_without_named_employer_is_unilateral_change():
    text = "Người lao động sẵn sàng chấp nhận mọi sự điều động khi có yêu cầu."
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


def test_open_company_bonus_rule_is_ambiguous():
    assert ("EMPLOYEE", "BONUS_BENEFITS", "AMBIGUOUS") in detect_dev_m2_risks(
        "Tiền thưởng và phụ cấp được xác định theo quy định của Công ty.")


def test_overtime_requires_open_employer_discretion():
    label = ("EMPLOYEE", "WORKING_HOURS_OVERTIME", "AMBIGUOUS")
    assert label in detect_dev_m2_risks(
        "Người lao động tăng ca theo tính chất công việc của Công ty.")
    assert label not in detect_dev_m2_risks(
        "Làm thêm giờ theo thỏa thuận của hai bên.")


def test_rest_rule_requires_open_employer_discretion():
    label = ("EMPLOYEE", "REST_AND_LEAVE", "AMBIGUOUS")
    assert label in detect_dev_m2_risks(
        "Ngày nghỉ bù được bố trí tùy theo tình hình do Ban lãnh đạo Công ty quyết định.")
    assert label not in detect_dev_m2_risks(
        "Ngày nghỉ bù theo lịch đã thỏa thuận giữa hai bên.")
