"""Clause Graph builder — NEXT, PARENT_OF và REFERS_TO (TDD §12.1, C-14 (a)(b), FR-31).

REFERS_TO chỉ dựng khi truyền `masked_text`: "Điều N" / "Khoản|Mục K Điều N" (cả `DIEU`, số thập phân
`1.2` dưới Điều 1) trên masked text; chỉ tạo cạnh khi resolve DUY NHẤT trong cùng hợp đồng. Dẫn chiếu văn
bản pháp luật (tên văn bản đứng NGAY sau số Điều: "Điều 26 Bộ luật…", "Điều 1 của Luật…") bị bỏ, không
diagnostic. Mơ hồ / không tìm thấy ⇒ bỏ cạnh + diagnostic AMBIGUOUS_REFERENCE / UNRESOLVED_REFERENCE.

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

import re
from dataclasses import dataclass
from typing import Optional, Sequence

from app.clause.segmenter import SegmentedClause
from app.core.enums import ClauseEdgeType
from app.domain.errors import PipelineInternalError

CLAUSE_GRAPH_VERSION = "clause_graph_v2"  # v2: thêm REFERS_TO (C-14 b)
_ARTICLE_HEADING = re.compile(r"(?i)^\s*(?:Điều|DIEU)\s+(\d+[a-z]?)\b")
_REFERENCE = re.compile(r"(?i)(?:(?:Khoản|Mục)\s+(?P<sub>\d+(?:\.\d+)?)\s+)?"
                        r"(?:Điều|DIEU)\s+(?P<article>\d+[a-z]?)\b")
# Tên văn bản pháp luật đứng ngay sau số Điều (tùy chọn "của/tại/theo"). Chỉ xét NGAY SAU để
# "Khoản 1 Điều 2 và Điều 26 Bộ luật Lao động" vẫn giữ dẫn chiếu nội bộ tới Điều 2.
_EXTERNAL_LAW = re.compile(r"(?i)^[\s,]*(?:(?:của|tại|theo)\s+)?(?:bộ\s+luật|luật|nghị\s+định|thông\s+tư|"
                           r"pháp\s+lệnh|pháp\s+luật|quyết\s+định|nghị\s+quyết|hiến\s+pháp|"
                           r"văn\s+bản\s+pháp\s+luật|blld|bllđ)\b")


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
    masked_text: Optional[str] = None,
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

    if masked_text is not None:
        edges.extend(_reference_edges(clauses, masked_text, diagnostics))

    graph = ClauseGraph(node_ids=tuple(ids), edges=tuple(edges))
    _validate(graph)
    return graph, diagnostics


def _reference_edges(
    clauses: Sequence[SegmentedClause], masked_text: str, diagnostics: list[Diagnostic],
) -> list[ClauseEdge]:
    """Resolve only unique within-contract references, without storing source text."""
    article_ids: dict[str, list[str]] = {}
    for c in clauses:
        if not (0 <= c.start_char < c.end_char <= len(masked_text)):
            raise PipelineInternalError("CLAUSE_GRAPH: masked span invalid")
        first_line = masked_text[c.start_char:c.end_char].split("\n", 1)[0]
        heading = _ARTICLE_HEADING.match(first_line)
        if c.structure.level == 1 and heading:
            article_ids.setdefault(heading.group(1).lower(), []).append(c.clause_id)

    sub_ids: dict[tuple[str, str], list[str]] = {}
    for c in clauses:
        parent = c.structure.parent_clause_id
        if not parent or not c.structure.number:
            continue
        parents = [number for number, ids in article_ids.items() if parent in ids]
        if len(parents) != 1:
            continue
        article = parents[0]
        number = c.structure.number.lower()
        if number.startswith(article + "."):
            number = number[len(article) + 1:]
        sub_ids.setdefault((article, number), []).append(c.clause_id)

    out: list[ClauseEdge] = []
    seen: set[tuple[str, str]] = set()
    reported: set[tuple[str, str]] = set()
    for c in clauses:
        text = masked_text[c.start_char:c.end_char]
        for match in _REFERENCE.finditer(text):
            # The clause's own opening heading is not a cross-reference.
            if match.start() == 0 and _ARTICLE_HEADING.match(text):
                continue
            after = text[match.end():match.end() + 64].split("\n", 1)[0]
            if _EXTERNAL_LAW.match(after):
                continue
            article = match.group("article").lower()
            sub = match.group("sub")
            targets = (sub_ids.get((article, sub.lower()), []) if sub
                       else article_ids.get(article, []))
            code = ("UNRESOLVED_REFERENCE" if not targets else
                    "AMBIGUOUS_REFERENCE" if len(targets) > 1 else None)
            if code:
                if (c.clause_id, code) not in reported:
                    diagnostics.append(Diagnostic(code, c.clause_id))
                    reported.add((c.clause_id, code))
                continue
            target = targets[0]
            if target != c.clause_id and (c.clause_id, target) not in seen:
                out.append(ClauseEdge(c.clause_id, target, ClauseEdgeType.REFERS_TO))
                seen.add((c.clause_id, target))
    return out


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
