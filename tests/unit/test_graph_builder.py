"""C-14 (a): Clause Graph NEXT + PARENT_OF (TDD §12.1)."""

import pytest
from app.clause.graph_builder import ClauseEdge, ClauseGraph, build_clause_graph
from app.clause.segmenter import ClauseStructure, SegmentedClause, segment
from app.core.enums import ClauseEdgeType
from app.domain.errors import PipelineInternalError
from app.privacy.pii_types import PiiSpan, PiiType

N, P = ClauseEdgeType.NEXT, ClauseEdgeType.PARENT_OF


def mk(i, level=1, parent=None, number=None):
    return SegmentedClause(f"cl_{i:04d}", f"text {i}", 0, 1, ClauseStructure(level, number, parent))


def cid(i):
    return f"cl_{i:04d}"


def test_next_chain_and_parent_of_from_hierarchy():
    cs = [mk(1), mk(2, 1), mk(3, 2, cid(2)), mk(4, 2, cid(2)), mk(5, 1)]
    g, diag = build_clause_graph(cs)
    assert g.node_ids == tuple(cid(i) for i in range(1, 6))
    assert [(e.src, e.dst) for e in g.edges_of(N)] == [(cid(i), cid(i + 1)) for i in range(1, 5)]
    assert [(e.src, e.dst) for e in g.edges_of(P)] == [(cid(2), cid(3)), (cid(2), cid(4))]
    assert g.children_of(cid(2)) == [cid(3), cid(4)] and g.parent_of(cid(3)) == cid(2)
    assert g.parent_of(cid(2)) is None and g.next_of(cid(5)) is None and g.prev_of(cid(1)) is None
    assert g.next_of(cid(1)) == cid(2) and g.prev_of(cid(3)) == cid(2)
    assert diag == []


def test_three_level_chain_and_determinism():
    cs = [mk(1), mk(2, 2, cid(1)), mk(3, 3, cid(2))]
    a, _ = build_clause_graph(cs)
    b, _ = build_clause_graph(list(cs))
    assert a == b and a.to_dict() == b.to_dict()
    assert a.parent_of(cid(3)) == cid(2) and a.parent_of(cid(2)) == cid(1)


def test_single_and_empty_input():
    g, _ = build_clause_graph([mk(1)])
    assert g.edges == ()
    g0, d0 = build_clause_graph([])
    assert g0.node_ids == () and g0.edges == () and d0 == []


def test_orphan_nested_is_diagnostic_not_error():
    g, diag = build_clause_graph([mk(1), mk(2, 2, None)])
    assert g.edges_of(P) == [] and len(g.edges_of(N)) == 1
    assert [(d.code, d.clause_id) for d in diag] == [("ORPHAN_NESTED", cid(2))]


@pytest.mark.parametrize("clauses", [
    [mk(1), mk(1)],                                  # id trùng
    [mk(1, 1, cid(1))],                              # self-loop
    [mk(1), mk(2, 2, "cl_0099")],                    # cha không tồn tại
    [mk(1, 2, cid(2)), mk(2, 1)],                    # cha đứng sau con
    [mk(1, 2), mk(2, 2, cid(1))],                    # level cha == level con
    [mk(1, 3), mk(2, 2, cid(1))],                    # level cha > level con
])
def test_invalid_hierarchy_raises_internal_error(clauses):
    with pytest.raises(PipelineInternalError):
        build_clause_graph(clauses)


def test_cycle_and_multi_parent_detected_by_validator():
    from app.clause.graph_builder import _validate

    cyc = ClauseGraph(("a", "b"), (ClauseEdge("a", "b", P), ClauseEdge("b", "a", P)))
    with pytest.raises(PipelineInternalError):
        _validate(cyc)
    two = ClauseGraph(("a", "b", "c"), (ClauseEdge("a", "c", P), ClauseEdge("b", "c", P)))
    with pytest.raises(PipelineInternalError):
        _validate(two)
    dangling = ClauseGraph(("a",), (ClauseEdge("a", "z", N),))
    with pytest.raises(PipelineInternalError):
        _validate(dangling)


CONTRACT = (
    "HỢP ĐỒNG LAO ĐỘNG\nHai bên thỏa thuận như sau, đầy đủ các điều kiện bên dưới đây.\n"
    "Điều 1. Công việc\n1.1 Người lao động làm việc tại văn phòng công ty\n1.2 Thời gian làm việc 8 giờ mỗi ngày\n"
    "Điều 2. Tiền lương\n2.1 Lương cơ bản 10.000.000 đồng mỗi tháng\n"
)


def test_graph_on_real_segmentation_has_one_parent_per_nested_clause_and_leaves_spans_untouched():
    res = segment(CONTRACT, CONTRACT, [])
    before = [(c.clause_id, c.start_char, c.end_char, c.original_text) for c in res.clauses]
    g, diag = build_clause_graph(res.clauses, CONTRACT)
    after = [(c.clause_id, c.start_char, c.end_char, c.original_text) for c in res.clauses]
    assert before == after  # graph không đổi segmentation/span
    nested = [c for c in res.clauses if c.structure.parent_clause_id]
    assert len(g.edges_of(P)) == len(nested) >= 3
    assert len(g.edges_of(N)) == len(res.clauses) - 1
    assert diag == []


def test_graph_when_heading_dropped_by_pii_placeholder_keeps_valid_tree():
    text = CONTRACT
    pos = text.index("1.2")
    spans = [PiiSpan(PiiType.PERSON_NAME, pos, pos + 3)]  # heading 1.2 nằm trong placeholder → bị bỏ
    res = segment(text, text, spans)
    g, _ = build_clause_graph(res.clauses)
    assert len(g.edges_of(N)) == len(res.clauses) - 1


def _graph_from_source(source):
    segmentation = segment(source, source, [])
    graph, diagnostics = build_clause_graph(segmentation.clauses, source)
    return segmentation, graph, diagnostics


def test_internal_article_reference_and_legal_reference_exclusion():
    source = ("Điều 1. Công việc\n"
              "Điều 2. Trách nhiệm\n"
              "1.1 Thực hiện theo Điều 1 của Hợp đồng này.\n"
              "1.2 Thực hiện theo Điều 26 Bộ luật Lao động 2019.")
    clauses, graph, diagnostics = _graph_from_source(source)
    refs = graph.edges_of(ClauseEdgeType.REFERS_TO)
    assert [(e.src, e.dst) for e in refs] == [(clauses.clauses[2].clause_id,
                                               clauses.clauses[0].clause_id)]
    assert not diagnostics


def test_reference_self_loop_unresolved_and_ambiguous():
    source = ("Điều 1. Tên điều\n"
              "Điều 1. Tên điều trùng\n"
              "Điều 2. Nội dung\n"
              "1.1 Theo Điều 1 của Hợp đồng này và Điều 99 của Hợp đồng này.")
    clauses, graph, diagnostics = _graph_from_source(source)
    assert graph.edges_of(ClauseEdgeType.REFERS_TO) == []
    assert [(d.code, d.clause_id) for d in diagnostics] == [
        ("AMBIGUOUS_REFERENCE", clauses.clauses[-1].clause_id),
        ("UNRESOLVED_REFERENCE", clauses.clauses[-1].clause_id),
    ]


def test_khoan_reference_resolves_unique_child():
    source = ("Điều 1. Nội dung\n"
              "1.1 Khoản thứ nhất.\n"
              "1.2 Khoản thứ hai.\n"
              "Điều 2. Dẫn chiếu\n"
              "1.1 Theo Khoản 2 Điều 1 của Hợp đồng này.")
    clauses, graph, _ = _graph_from_source(source)
    assert [(e.src, e.dst) for e in graph.edges_of(ClauseEdgeType.REFERS_TO)] == [
        (clauses.clauses[-1].clause_id, clauses.clauses[2].clause_id)]


@pytest.mark.parametrize("law_name", [
    "Bộ luật Lao động", "Luật Lao động", "Nghị định 145", "Thông tư 01",
    "Pháp lệnh", "Quyết định 10", "Hiến pháp", "văn bản pháp luật",
])
def test_external_law_references_never_create_contract_edges(law_name):
    source = f"Điều 1. Nội dung\nĐiều 2. Thực hiện theo Điều 1 của {law_name}."
    _, graph, diagnostics = _graph_from_source(source)
    assert graph.edges_of(ClauseEdgeType.REFERS_TO) == []
    assert not diagnostics


def test_self_reference_and_duplicate_mentions_do_not_duplicate_edges():
    source = ("Điều 1. Nội dung theo Điều 1 của Hợp đồng này.\n"
              "DIEU 2. Xem Điều 1 của Hợp đồng này; xem lại Điều 1 của Hợp đồng này.")
    clauses, graph, diagnostics = _graph_from_source(source)
    assert [(e.src, e.dst) for e in graph.edges_of(ClauseEdgeType.REFERS_TO)] == [
        (clauses.clauses[1].clause_id, clauses.clauses[0].clause_id)]
    assert not diagnostics
