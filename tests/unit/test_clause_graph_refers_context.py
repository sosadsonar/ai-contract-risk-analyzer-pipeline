"""C-14 (b): REFERS_TO loại trừ dẫn chiếu luật; resolve_risk_context + trace; X-21 context chung (FR-33)."""

import json

import pytest
from app.clause.context_resolver import resolve_risk_context
from app.clause.graph_builder import CLAUSE_GRAPH_VERSION, build_clause_graph
from app.clause.segmenter import segment
from app.core.enums import ClauseEdgeType
from app.privacy.masker import mask

# fixture refers_contract + excludes_legal_reference (TDD §12, PROGRESS T5)
CONTRACT = """HỢP ĐỒNG LAO ĐỘNG
Điều 1. Công việc
Người lao động làm chuyên viên kế toán tại trụ sở công ty theo phân công.
Điều 2. Thời gian thử việc
1. Thời gian thử việc là 90 ngày kể từ ngày ký.
2. Lương thử việc bằng 85% mức lương quy định tại Điều 3.
Điều 3. Tiền lương
Mức lương chính 10.000.000 đồng/tháng; điều chỉnh theo Khoản 1 Điều 2 và Điều 26 Bộ luật Lao động.
Điều 4. Chấm dứt
Người lao động thực hiện theo Điều 35 của Bộ luật Lao động 2019 và Điều 9 hợp đồng này.
Điều 5. Thời hạn hợp đồng
Hợp đồng xác định thời hạn 12 tháng."""


@pytest.fixture(scope="module")
def built():
    m = mask(CONTRACT)
    seg = segment(CONTRACT, m.masked_text, m.pii_spans)
    graph, diags = build_clause_graph(seg.clauses, m.masked_text)
    by_text = {c.original_text.split("\n")[0][:20]: c.clause_id for c in seg.clauses}
    masked = {c.clause_id: m.masked_text[c.start_char:c.end_char] for c in seg.clauses}
    return seg, graph, diags, by_text, masked


def _id(by_text, prefix):
    return next(v for k, v in by_text.items() if k.startswith(prefix))


def test_version():
    assert CLAUSE_GRAPH_VERSION == "clause_graph_v2"


def test_refers_to_internal_article_and_item(built):
    _, graph, _, by_text, _ = built
    refs = {(e.src, e.dst) for e in graph.edges_of(ClauseEdgeType.REFERS_TO)}
    assert (_id(by_text, "2. Lương thử việc"), _id(by_text, "Điều 3")) in refs
    assert (_id(by_text, "Điều 3"), _id(by_text, "1. Thời gian thử")) in refs
    assert len(refs) == 2


def test_legal_references_excluded_and_unresolved_reported(built):
    _, graph, diags, by_text, _ = built
    codes = [(d.code, d.clause_id) for d in diags]
    # Dẫn chiếu luật (Điều 26 Bộ luật…, Điều 35 của Bộ luật…) bị bỏ, không diagnostic.
    assert codes == [("UNRESOLVED_REFERENCE", _id(by_text, "Điều 4"))]       # Điều 9 không tồn tại
    assert not any(e.src == _id(by_text, "Điều 4") for e in graph.edges_of(ClauseEdgeType.REFERS_TO))


def test_ambiguous_reference_dropped():
    text = "Điều 1. A\nNội dung một.\nĐiều 1. B\nNội dung hai.\nĐiều 2. C\nXem Điều 1."
    m = mask(text)
    seg = segment(text, m.masked_text, m.pii_spans)
    graph, diags = build_clause_graph(seg.clauses, m.masked_text)
    assert graph.edges_of(ClauseEdgeType.REFERS_TO) == []
    assert any(d.code == "AMBIGUOUS_REFERENCE" for d in diags)


def test_without_masked_text_only_structural_edges(built):
    seg, _, _, _, _ = built
    graph, _ = build_clause_graph(seg.clauses)
    assert graph.edges_of(ClauseEdgeType.REFERS_TO) == []


def test_graph_serialization_has_no_text(built):
    _, graph, diags, _, _ = built
    blob = json.dumps(graph.to_dict(), ensure_ascii=False) + repr(diags)
    assert "Tiền lương" not in blob and "Điều" not in blob


def test_resolve_context_priority_and_trace_has_no_text(built):
    _, graph, _, by_text, masked = built
    target = _id(by_text, "2. Lương thử việc")
    labels = {cid: ["OTHER"] for cid in masked}
    items, trace = resolve_risk_context(target, graph, masked, labels, max_related=3, max_context_chars=6000)
    relations = [(i.clause_id, i.relation) for i in items]
    assert relations[0] == (_id(by_text, "Điều 3"), "REFERS_TO")
    assert relations[1] == (_id(by_text, "Điều 2"), "PARENT_OF")
    assert relations[2] == (_id(by_text, "1. Thời gian thử"), "PREVIOUS")
    # NEXT của target chính là Điều 3 (đã lấy qua REFERS_TO) ⇒ khử trùng, không có gì bị cắt.
    assert len(items) == 3 and trace.truncated is False
    dumped = json.dumps(trace.to_dict(), ensure_ascii=False)
    assert "lương" not in dumped.lower() and trace.context_chars == sum(len(i.masked_text) for i in items)


def test_incoming_refers_to_and_char_cap(built):
    _, graph, _, by_text, masked = built
    target = _id(by_text, "Điều 3")
    labels = {cid: ["OTHER"] for cid in masked}
    items, _ = resolve_risk_context(target, graph, masked, labels, max_related=3, max_context_chars=6000)
    assert [i.relation for i in items][:2] == ["REFERS_TO", "REFERRED_BY"]
    small, trace = resolve_risk_context(target, graph, masked, labels, max_related=3, max_context_chars=10)
    assert small == [] and trace.truncated is True


def test_common_context_job_info_and_contract_term(built):
    """X-21 / FR-33: hợp đồng thử việc 90 ngày kèm clause chức danh và loại hợp đồng."""
    _, graph, _, by_text, masked = built
    target = _id(by_text, "1. Thời gian thử")
    labels = {cid: ["OTHER"] for cid in masked}
    labels[_id(by_text, "Điều 1")] = ["JOB_INFO"]
    labels[_id(by_text, "Điều 5")] = ["CONTRACT_TERM"]
    items, trace = resolve_risk_context(target, graph, masked, labels, max_related=3, max_context_chars=6000)
    rel = {i.relation: i.clause_id for i in items}
    assert rel["COMMON_JOB_INFO"] == _id(by_text, "Điều 1")
    assert rel["COMMON_CONTRACT_TERM"] == _id(by_text, "Điều 5")
    assert {r["relation"] for r in trace.to_dict()["related"]} >= {"COMMON_JOB_INFO", "COMMON_CONTRACT_TERM"}


def test_graph_disabled_returns_no_context(built):
    _, _, _, by_text, masked = built
    items, trace = resolve_risk_context(_id(by_text, "Điều 3"), None, masked, {})
    assert items == [] and trace.included_in_risk_request is False
