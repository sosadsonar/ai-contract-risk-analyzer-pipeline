import pytest

from app.ai.risk_adapter import RiskItemIn, attach_graph_context
from app.clause.context_resolver import resolve_context
from app.clause.graph_builder import ClauseEdge, ClauseGraph
from app.core.enums import ClauseEdgeType


def _graph():
    ids = tuple(f"cl_{i:04}" for i in range(1, 7))
    edges = (
        ClauseEdge(ids[1], ids[4], ClauseEdgeType.REFERS_TO),
        ClauseEdge(ids[2], ids[1], ClauseEdgeType.REFERS_TO),
        ClauseEdge(ids[0], ids[1], ClauseEdgeType.PARENT_OF),
        ClauseEdge(ids[1], ids[3], ClauseEdgeType.PARENT_OF),
        ClauseEdge(ids[0], ids[1], ClauseEdgeType.NEXT),
        ClauseEdge(ids[1], ids[2], ClauseEdgeType.NEXT),
    )
    return ClauseGraph(ids, edges)


def test_context_priority_dedup_and_risk_payload():
    graph = _graph()
    masked = {cid: f"masked {cid}" for cid in graph.node_ids}
    context = resolve_context(graph, "cl_0002", masked)
    assert [(c.clause_id, c.relation) for c in context] == [
        ("cl_0005", "REFERS_TO"), ("cl_0003", "REFERRED_BY"),
        ("cl_0001", "PARENT_OF"),
    ]
    item = RiskItemIn("cl_0002", masked["cl_0002"], [])
    enriched = attach_graph_context([item], graph, masked)
    assert item.related_clauses == []
    assert [c["clause_id"] for c in enriched[0].to_payload()["related_clauses"]] == [
        "cl_0005", "cl_0003", "cl_0001",
    ]
    assert all(c["masked_text"] == masked[c["clause_id"]]
               for c in enriched[0].to_payload()["related_clauses"])


def test_context_limit_counts_unicode_code_points_and_skips_oversize():
    graph = _graph()
    masked = {cid: "x" for cid in graph.node_ids}
    masked["cl_0005"] = "á" * 6001
    masked["cl_0003"] = "é" * 5999
    masked["cl_0001"] = "đ" * 2
    context = resolve_context(graph, "cl_0002", masked)
    assert [c.clause_id for c in context] == ["cl_0003", "cl_0004"]
    assert sum(len(c.masked_text) for c in context) == 6000


def test_context_zero_limits_and_unknown_target():
    graph = _graph()
    masked = {cid: "text" for cid in graph.node_ids}
    assert resolve_context(graph, "cl_0002", masked, max_related=0) == []
    assert resolve_context(graph, "cl_0002", masked, max_context_chars=0) == []
    with pytest.raises(ValueError, match="unknown target"):
        resolve_context(graph, "cl_9999", masked)
