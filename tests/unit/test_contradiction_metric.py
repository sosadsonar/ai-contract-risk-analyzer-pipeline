"""M10 (X-27, N1): recall/báo nhầm trên cặp D3, graph tắt/mở."""

import pytest

from ai_pipeline.evaluation.metrics.contradiction import (
    ClausePair,
    RiskLink,
    compare_graph_on_off,
    evaluate_contradiction,
)

PAIRS = [
    ClausePair("p1", "D3_001", "cl_0003", "cl_0007", True),
    ClausePair("p2", "D3_001", "cl_0004", "cl_0009", True),
    ClausePair("c1", "D3_001", "cl_0002", "cl_0005", False),
    ClausePair("p3", "D3_002", "cl_0010", "cl_0011", True),
    ClausePair("c2", "D3_002", "cl_0001", "cl_0002", False),
]


def test_detected_in_either_direction_and_false_alarms():
    risks = [RiskLink("D3_001", "cl_0007", ("cl_0003",), "AMBIGUOUS"),     # p1 (chiều b→a)
             RiskLink("D3_002", "cl_0010", ("cl_0011",), "UNFAVORABLE"),   # p3, basis khác
             RiskLink("D3_001", "cl_0002", ("cl_0005",), "AMBIGUOUS")]     # c1 báo nhầm
    r = evaluate_contradiction(PAIRS, risks)
    assert (r.detected, r.contradictory_total, r.recall) == (2, 3, pytest.approx(2 / 3))
    assert (r.false_alarms, r.control_total, r.false_alarm_rate) == (1, 2, 0.5)
    assert r.missed_pair_ids == ("p2",) and r.false_alarm_pair_ids == ("c1",)
    strict = evaluate_contradiction(PAIRS, risks, require_ambiguous=True)
    assert strict.detected == 1


def test_document_scoped_links():
    risks = [RiskLink("D3_002", "cl_0003", ("cl_0007",))]  # cùng ID nhưng tài liệu khác
    assert evaluate_contradiction(PAIRS, risks).detected == 0


def test_graph_on_off_comparison():
    out = compare_graph_on_off(PAIRS, {"graph_off": [], "graph_on": [RiskLink("D3_001", "cl_0003", ("cl_0007",))]})
    assert out["graph_off"]["detected"] == 0 and out["graph_on"]["detected"] == 1
    with pytest.raises(ValueError):
        compare_graph_on_off(PAIRS, {"on": []})


def test_invalid_pairs_rejected():
    with pytest.raises(ValueError):
        evaluate_contradiction([PAIRS[0], PAIRS[0]], [])
    with pytest.raises(ValueError):
        evaluate_contradiction([ClausePair("x", "D", "cl_0001", "cl_0001", True)], [])
