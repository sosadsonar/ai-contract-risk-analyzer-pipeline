"""INV-08: Clause Graph không chứa text (serialize + duyệt object). SKELETON §9."""

import dataclasses
import json
import re
from enum import Enum

from app.clause.graph_builder import Diagnostic, build_clause_graph
from app.clause.segmenter import ClauseStructure, SegmentedClause, segment
from app.core.enums import ClauseEdgeType

SECRET = "BÍ-MẬT-LƯƠNG-12345678-Nguyễn Văn An"
CLAUSE_ID = re.compile(r"^cl_[0-9]{4}$")
EDGE_NAMES = {e.value for e in ClauseEdgeType}


def _walk(obj, path="graph"):
    """Yield (path, giá trị lá). Duyệt dataclass, tuple/list/dict, enum — mọi lá phải là ID/tên cạnh/số."""
    if dataclasses.is_dataclass(obj):
        for f in dataclasses.fields(obj):
            yield from _walk(getattr(obj, f.name), f"{path}.{f.name}")
    elif isinstance(obj, (list, tuple, set, frozenset)):
        for i, x in enumerate(obj):
            yield from _walk(x, f"{path}[{i}]")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk(k, f"{path}.<key>")
            yield from _walk(v, f"{path}[{k!r}]")
    elif isinstance(obj, Enum):
        yield path, obj.value
    else:
        yield path, obj


def _clauses():
    text = f"Điều 1. Lương\n1.1 {SECRET}\n1.2 thêm nội dung dài hơn bốn mươi ký tự để không bị gộp\n"
    return text, segment(text, text, []).clauses


def test_graph_object_graph_has_only_ids_and_edge_names():
    _, clauses = _clauses()
    g, diags = build_clause_graph(clauses)
    for path, leaf in _walk(g):
        assert isinstance(leaf, str) and (CLAUSE_ID.match(leaf) or leaf in EDGE_NAMES), (path, leaf)
    for d in diags:
        assert isinstance(d, Diagnostic) and d.code.isupper()


def test_serialized_graph_does_not_contain_clause_text_or_offsets_or_numbers():
    text, clauses = _clauses()
    g, _ = build_clause_graph(clauses, text)
    blob = json.dumps(g.to_dict(), ensure_ascii=False)
    for c in clauses:
        assert c.original_text not in blob
    assert SECRET not in blob and "Lương" not in blob
    assert set(g.to_dict()) == {"version", "node_ids", "edges"}
    for e in g.to_dict()["edges"]:
        assert set(e) == {"src", "dst", "edge_type"}
    for forbidden in ("start_char", "end_char", "original_text", "number", "level", "masked"):
        assert forbidden not in blob


def test_graph_classes_have_no_free_text_fields():
    from app.clause.graph_builder import ClauseEdge, ClauseGraph

    assert {f.name for f in dataclasses.fields(ClauseGraph)} == {"node_ids", "edges"}
    assert {f.name for f in dataclasses.fields(ClauseEdge)} == {"src", "dst", "edge_type"}
    assert {f.name for f in dataclasses.fields(Diagnostic)} == {"code", "clause_id"}


def test_diagnostics_never_carry_text_even_for_orphans():
    cs = [SegmentedClause("cl_0001", SECRET, 0, 5, ClauseStructure(2, "1.1", None))]
    _, diags = build_clause_graph(cs)
    assert diags and all(SECRET not in repr(d) for d in diags)
