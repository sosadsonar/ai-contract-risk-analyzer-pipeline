"""Clause Graph builder — cạnh NEXT + PARENT_OF + REFERS_TO (TDD §12.1, C-14 (a)(b), FR-31).

REFERS_TO (C-14 b, W5): chỉ dựng khi truyền `masked_text`; regex "Điều N" / "Khoản K Điều N" trên
masked text của từng clause, loại trừ dẫn chiếu văn bản pháp luật (Bộ luật, Luật, Nghị định, Thông tư,
văn bản pháp luật...), chỉ tạo cạnh khi resolve đúng DUY NHẤT tới clause trong cùng hợp đồng; mơ hồ
hoặc không tìm thấy ⇒ bỏ cạnh + diagnostic.

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
    masked_text: Optional[str] = None,  # có ⇒ dựng REFERS_TO; None ⇒ chỉ cạnh cấu trúc
) -> tuple[ClauseGraph, list[Diagnostic]]:
    """Dựng Clause Graph từ kết quả segmentation (thứ tự văn bản).

    NEXT: `clauses[i] -> clauses[i+1]`. PARENT_OF: `structure.parent_clause_id -> clause_id`
    (hierarchy numbering do `structure_parser` gán). Cạnh sinh theo thứ tự xác định.

    Diagnostic (không chặn): `ORPHAN_NESTED` — clause level > 1 mà không có cha (heading cha bị bỏ
    vì nằm trong placeholder PII và không còn mark cha nào); mất cạnh PARENT_OF nhưng vẫn có NEXT.
    `REFERS_TO_AMBIGUOUS` / `REFERS_TO_UNRESOLVED` / `REFERS_TO_LEGAL_EXCLUDED` — dẫn chiếu bị bỏ.

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
        ref_edges, ref_diags = _refers_to_edges(clauses, masked_text)
        edges.extend(ref_edges)
        diagnostics.extend(ref_diags)

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


# ---------------------------------------------------------------------------------------------
# REFERS_TO (C-14 b)
# ---------------------------------------------------------------------------------------------

_ARTICLE_HEAD = re.compile(r"^\s*Điều\s+(\d+[a-zđ]?)\b", re.IGNORECASE)
_ITEM_HEAD = re.compile(r"^\s*(?:Khoản\s+)?(\d{1,3})[.)]?\s", re.IGNORECASE)
_REFERENCE = re.compile(
    r"(?:\b[Kk]hoản\s+(?P<item>\d{1,3})\s+(?:của\s+)?)?\b[Đđ]iều\s+(?P<article>\d+[a-zđ]?)\b"
)
# Ngữ cảnh ngay sau dẫn chiếu chỉ ra văn bản pháp luật bên ngoài ⇒ không phải dẫn chiếu nội bộ.
_LEGAL_AFTER = re.compile(
    r"^[\s,]*(?:của\s+|tại\s+|theo\s+)?(?:bộ\s+luật|luật|nghị\s+định|thông\s+tư|văn\s+bản\s+pháp\s+luật|"
    r"pháp\s+luật|blld|bllđ|nđ|tt|quyết\s+định|nghị\s+quyết|hiến\s+pháp)",
    re.IGNORECASE,
)
_LOOKAHEAD = 60


def _structure_index(clauses: Sequence[SegmentedClause], masked_text: str):
    """article number → [clause_id]; (article, item) → [clause_id]. Chỉ dựa vào heading đầu clause."""
    articles: dict[str, list[str]] = {}
    items: dict[tuple[str, str], list[str]] = {}
    article_of: dict[str, str] = {}
    for c in clauses:
        head = masked_text[c.start_char:c.end_char]
        m = _ARTICLE_HEAD.match(head)
        if m:
            num = m.group(1).lower()
            articles.setdefault(num, []).append(c.clause_id)
            article_of[c.clause_id] = num
    for c in clauses:
        parent = c.structure.parent_clause_id
        if parent in article_of and c.structure.number is not None:
            m = _ITEM_HEAD.match(masked_text[c.start_char:c.end_char])
            if m and m.group(1) == c.structure.number:
                items.setdefault((article_of[parent], c.structure.number), []).append(c.clause_id)
    return articles, items, article_of


def _refers_to_edges(clauses: Sequence[SegmentedClause], masked_text: str):
    articles, items, article_of = _structure_index(clauses, masked_text)
    own_article: dict[str, Optional[str]] = {}
    for c in clauses:
        own_article[c.clause_id] = article_of.get(c.clause_id) or article_of.get(c.structure.parent_clause_id or "")
    edges: list[ClauseEdge] = []
    diags: list[Diagnostic] = []
    seen: set[tuple[str, str]] = set()
    for c in clauses:
        body = masked_text[c.start_char:c.end_char]
        head = _ARTICLE_HEAD.match(body)
        scan_from = head.end() if head else 0  # bỏ chính heading "Điều N." của clause
        for m in _REFERENCE.finditer(body, scan_from):
            after = body[m.end():m.end() + _LOOKAHEAD]
            if _LEGAL_AFTER.match(after):
                diags.append(Diagnostic("REFERS_TO_LEGAL_EXCLUDED", c.clause_id))
                continue
            article = m.group("article").lower()
            item = m.group("item")
            targets = items.get((article, item), []) if item else articles.get(article, [])
            if len(targets) != 1:
                code = "REFERS_TO_AMBIGUOUS" if len(targets) > 1 else "REFERS_TO_UNRESOLVED"
                diags.append(Diagnostic(code, c.clause_id))
                continue
            dst = targets[0]
            # "Điều này"/tự dẫn chiếu tới chính clause hoặc Điều chứa nó không phải quan hệ mới.
            if dst == c.clause_id or (item is None and own_article.get(c.clause_id) == article
                                      and dst == c.structure.parent_clause_id):
                continue
            if (c.clause_id, dst) not in seen:
                seen.add((c.clause_id, dst))
                edges.append(ClauseEdge(c.clause_id, dst, ClauseEdgeType.REFERS_TO))
    return edges, diags
