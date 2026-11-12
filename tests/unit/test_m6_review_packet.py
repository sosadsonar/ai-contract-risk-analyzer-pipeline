import csv

import pytest

from scripts.score_m6_review_packet import score


def test_requires_real_40_rated_outputs(tmp_path):
    path = tmp_path / "ratings.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("output_id", "human_a", "human_b", "human_adjudicated", "judge"))
        for i in range(40):
            writer.writerow((f"real_{i}", "DUNG", "DUNG", "DUNG", "DUNG" if i < 32 else "SAI"))
    result = score(path)
    assert result["n"] == 40
    assert result["judge_human_agreement"] == 0.8
    assert result["m6_threshold_met"] is True  # agreement target; kappa is reported separately


def test_rejects_unfilled_packet(tmp_path):
    path = tmp_path / "ratings.csv"
    path.write_text("output_id,human_a,human_b,human_adjudicated,judge\n", encoding="utf-8")
    with pytest.raises(ValueError, match="40 unique"):
        score(path)


def test_wide_dev_candidate_packet_is_not_m6_acceptance(tmp_path):
    path = tmp_path / "dev_ratings.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("output_id", "document_id", "candidate_status", "human_a", "human_b", "human_adjudicated", "judge"))
        for i in range(40):
            writer.writerow((f"candidate_{i}", "HDLD001", "NEEDS_HUMAN_SOURCE_AND_CITATION_REVIEW", "DUNG", "DUNG", "DUNG", "DUNG"))
    result = score(path)
    assert result["status"] == "D2_DEV_REVIEW_AGREEMENT_NOT_M6_ACCEPTANCE"
    assert result["acceptance_scope_verified"] is False


def test_complete_40_ratings_agreement_and_kappa(tmp_path):
    path = tmp_path / "complete.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("output_id", "human_a", "human_b", "human_adjudicated", "judge"))
        for i in range(40):
            human = "DUNG" if i < 20 else "SAI"
            judge = ("SAI" if i in (0, 1) else "DUNG") if i < 20 else (
                "DUNG" if i in (20, 21) else "SAI")
            writer.writerow((f"output_{i:02}", human, human, human, judge))
    result = score(path)
    assert result["judge_human_agreement"] == pytest.approx(0.9)
    assert result["judge_human_kappa"] == pytest.approx(0.8)
    assert result["human_a_b_agreement"] == 1.0
    assert result["human_a_b_kappa"] == 1.0
    assert result["m6_threshold_met"] is True
    assert result["acceptance_scope_verified"] is False


def test_complete_constant_ratings_do_not_divide_by_zero(tmp_path):
    path = tmp_path / "constant.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("output_id", "human_a", "human_b", "human_adjudicated", "judge"))
        for i in range(40):
            writer.writerow((f"output_{i:02}", "DUNG", "DUNG", "DUNG", "DUNG"))
    result = score(path)
    assert result["judge_human_agreement"] == 1.0
    assert result["judge_human_kappa"] is None
    assert result["m6_threshold_met"] is True
