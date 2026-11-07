import pytest
from app.clause.dev_tfidf_baseline import DevTfidfBaseline


def test_exact_reference_recovers_its_label_without_test_labels():
    model = DevTfidfBaseline.fit(
        ["Thời hạn hợp đồng là mười hai tháng.", "Tiền lương được trả hằng tháng."],
        [("CONTRACT_TERM",), ("COMPENSATION_BENEFITS",)],
    )
    assert model.predict(["Tiền lương được trả hằng tháng."]) == (("COMPENSATION_BENEFITS",),)


def test_fit_requires_aligned_dev_examples():
    with pytest.raises(ValueError):
        DevTfidfBaseline.fit(["A"], [])
