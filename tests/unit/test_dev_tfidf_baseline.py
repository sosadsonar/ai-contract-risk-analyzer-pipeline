import pytest
from app.clause.dev_tfidf_baseline import DevTfidfBaseline, add_source_working_conditions


def test_exact_reference_recovers_its_label_without_test_labels():
    model = DevTfidfBaseline.fit(
        ["Thời hạn hợp đồng là mười hai tháng.", "Tiền lương được trả hằng tháng."],
        [("CONTRACT_TERM",), ("COMPENSATION_BENEFITS",)],
    )
    assert model.predict(["Tiền lương được trả hằng tháng."]) == (("COMPENSATION_BENEFITS",),)


def test_fit_requires_aligned_dev_examples():
    with pytest.raises(ValueError):
        DevTfidfBaseline.fit(["A"], [])


def test_source_security_signal_adds_second_clause_label_without_gold_lookup():
    texts = [
        "Khoản ký quỹ được hoàn trả khi hợp đồng kết thúc.",
        "Bên sử dụng lao động giữ bản chính giấy tờ.",
        "Hợp đồng chấm dứt theo thỏa thuận.",
        "Công ty bảo đảm an toàn lao động.",
    ]
    predictions = [("TERMINATION",)] * len(texts)
    assert add_source_working_conditions(texts, predictions) == (
        ("TERMINATION", "WORKING_CONDITIONS"),
        ("TERMINATION", "WORKING_CONDITIONS"),
        ("TERMINATION",),
        ("TERMINATION",),
    )


def test_source_security_signal_keeps_at_most_two_unique_labels():
    assert add_source_working_conditions(
        ["Người lao động phải đặt cọc tiền bảo đảm."],
        [("WORKING_CONDITIONS", "TERMINATION")],
    ) == (("WORKING_CONDITIONS", "TERMINATION"),)
    with pytest.raises(ValueError):
        add_source_working_conditions(["A"], [])
