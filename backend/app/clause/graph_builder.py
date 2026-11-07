"""Clause Graph builder — cạnh NEXT + PARENT_OF (TDD §12.1, C-14 (a), FR-31).

Phạm vi W4: chỉ NEXT và PARENT_OF. REFERS_TO (regex, loại trừ dẫn chiếu pháp luật) làm ở W5
(C-14 (b)); tham số `masked_text` đã có sẵn trong chữ ký để khỏi đổi API khi đó.

Bất biến:
  INV-08  graph CHỈ chứa `clause_id` + `edge_type` — không text, không offset, không số điều.
          `ClauseGraph`/`ClauseEdge` không có trường nào chứa nội dung; `to_dict()` chỉ trả ID + tên cạnh.
  Clause Graph không đổi segmentation/span (hàm chỉ ĐỌC `clauses`, không sửa chúng).
  Validation (TDD §12.1): node tồn tại, không self-loop, PARENT_OF có level cha < level con và
  không chu trình. Vi phạm = bug cục bộ ⇒ `PipelineInternalError` (→ FAILED, INTERNAL_ERROR),
  không phải lỗi người dùng.

Hàm thuần: không I/O, không import `api/` hay `session/`. Diagnostic cũng chỉ chứa ID + mã.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from app.clause.segmenter import SegmentedClause
from app.core.enums import ClauseEdgeType
from app.domain.errors import PipelineInternalError

CLAUSE_GRAPH_VERSION = "clause_graph_v1"


@dataclass(frozen=True)
class ClauseEdge:
    """Cạnh có hướng `src -> dst`. PARENT_OF: src là cha, dst là con. NEXT: src đứng ngay trước dst."""

    src: str
    dst: str
    edge_type: ClauseEdgeType


@dataclass(frozen=True)
class Diagnostic:
    """Ghi chú dựng graph. Chỉ ID + mã ổn định — KHÔNG chứa text hợp đồng (INV-08, INV-13)."""

    code: str
    clause_id: Optional[str] = None


@dataclass(frozen=True)
class ClauseGraph:
    node_ids: tuple[str, ...]
    edges: tuple[ClauseEdge, ...]

    def to_dict(self) -> dict:
        """Dạng serialize dùng cho test/dev trace: chỉ ID và tên loại cạnh."""
        return {
            "version": CLAUSE_GRAPH_VERSION,
            "node_ids": list(self.node_ids),
            "edges": [
                {"src": e.src, "dst": e.dst, "edge_type": e.edge_type.value} for e in self.edges
            ],
        }

    def edges_of(self, edge_type: ClauseEdgeType) -> list[ClauseEdge]:
        return [e for e in self.edges if e.edge_type == edge_type]

    def children_of(self, clause_id: str) -> list[str]:
        return [e.dst for e in self.edges if e.edge_type == ClauseEdgeType.PARENT_OF and e.src == clause_id]

    def parent_of(self, clause_id: str) -> Optional[str]:
        for e in self.edges:
            if e.edge_type == ClauseEdgeType.PARENT_OF and e.dst == clause_id:
                return e.src
        return None

    def next_of(self, clause_id: str) -> Optional[str]:
        for e in self.edges:
            if e.edge_type == ClauseEdgeType.NEXT and e.src == clause_id:
                return e.dst
        return None

    def prev_of(self, clause_id: str) -> Optional[str]:
        for e in self.edges:
            if e.edge_type == ClauseEdgeType.NEXT and e.dst == clause_id:
                return e.src
        return None


def build_clause_graph(
    clauses: Sequence[SegmentedClause],
    masked_text: Optional[str] = None,  # dành cho REFERS_TO (W5); W4 chưa dùng, không đọc
) -> tuple[ClauseGraph, list[Diagnostic]]:
    """Dựng Clause Graph từ kết quả segmentation (thứ tự văn bản).

    NEXT: `clauses[i] -> clauses[i+1]`. PARENT_OF: `structure.parent_clause_id -> clause_id`
    (hierarchy numbering do `structure_parser` gán). Cạnh sinh theo thứ tự xác định.

    Diagnostic (không chặn): `ORPHAN_NESTED` — clause level > 1 mà không có cha (heading cha bị bỏ
    vì nằm trong placeholder PII và không còn mark cha nào); mất cạnh PARENT_OF nhưng vẫn có NEXT.

    Raises:
        PipelineInternalError: clause_id trùng/rỗng, parent không tồn tại hoặc đứng sau con,
            self-loop, level cha >= level con (⇒ cũng loại chu trình).
    """
    ids = [c.clause_id for c in clauses]
    if len(set(ids)) != len(ids):
        raise PipelineInternalError("CLAUSE_GRAPH: clause_id trùng")
    index = {cid: i for i, cid in enumerate(ids)}
    level = {c.clause_id: c.structure.level for c in clauses}

    edges: list[ClauseEdge] = []
    diagnostics: list[Diagnostic] = []

    for a, b in zip(ids, ids[1:]):
        edges.append(ClauseEdge(a, b, ClauseEdgeType.NEXT))

    for c in clauses:
        parent = c.structure.parent_clause_id
        if parent is None:
            if c.structure.level > 1:
                diagnostics.append(Diagnostic("ORPHAN_NESTED", c.clause_id))
            continue
        if parent == c.clause_id:
            raise PipelineInternalError("CLAUSE_GRAPH: self-loop PARENT_OF")
        if parent not in index:
            raise PipelineInternalError("CLAUSE_GRAPH: parent_clause_id không tồn tại")
        if index[parent] >= index[c.clause_id]:
            raise PipelineInternalError("CLAUSE_GRAPH: cha phải đứng trước con")
        if level[parent] >= level[c.clause_id]:
            raise PipelineInternalError("CLAUSE_GRAPH: level cha phải nhỏ hơn level con")
        edges.append(ClauseEdge(parent, c.clause_id, ClauseEdgeType.PARENT_OF))

    graph = ClauseGraph(node_ids=tuple(ids), edges=tuple(edges))
    _validate(graph)
    return graph, diagnostics


def _validate(graph: ClauseGraph) -> None:
    """Kiểm lần cuối trên graph đã dựng (phòng thủ; dùng chung cho W5 khi thêm REFERS_TO)."""
    nodes = set(graph.node_ids)
    seen: set[tuple[str, str, ClauseEdgeType]] = set()
    for e in graph.edges:
        if e.src not in nodes or e.dst not in nodes:
            raise PipelineInternalError("CLAUSE_GRAPH: cạnh trỏ tới node không tồn tại")
        if e.src == e.dst:
            raise PipelineInternalError("CLAUSE_GRAPH: self-loop")
        key = (e.src, e.dst, e.edge_type)
        if key in seen:
            raise PipelineInternalError("CLAUSE_GRAPH: cạnh trùng")
        seen.add(key)
    _assert_parent_of_acyclic(graph)


def _assert_parent_of_acyclic(graph: ClauseGraph) -> None:
    parent: dict[str, str] = {}
    for e in graph.edges:
        if e.edge_type == ClauseEdgeType.PARENT_OF:
            if e.dst in parent:
                raise PipelineInternalError("CLAUSE_GRAPH: clause có nhiều hơn một cha")
            parent[e.dst] = e.src
    for start in parent:
        cur, hops = start, 0
        while cur in parent:
            cur = parent[cur]
            hops += 1
            if hops > len(graph.node_ids):
                raise PipelineInternalError("CLAUSE_GRAPH: PARENT_OF có chu trình")
