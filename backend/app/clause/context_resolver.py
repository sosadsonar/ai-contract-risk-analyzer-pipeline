"""Context Resolver cho Risk LLM (TDD §12.2–12.3, C-14 b, X-21 / FR-33).

Thứ tự ưu tiên related clauses của một target (TDD §12.2):
  1. REFERS_TO đi ra   2. REFERS_TO đi vào   3. cha trực tiếp, rồi con trực tiếp (PARENT_OF)
  4. NEXT trước, rồi NEXT sau
Khử trùng, bỏ target; tối đa `max_related` clause và `max_chars` code point (masked text) cho cả ngữ cảnh.

FR-33 (X-21): cấp THÊM context chung — clause đầu tiên có nhãn JOB_INFO và clause đầu tiên có nhãn
CONTRACT_TERM (SRS gọi là CONTRACT_TERM_TYPE; nhãn trong taxonomy là CONTRACT_TERM) — tối đa một clause
mỗi nhãn, không tính vào `max_related` nhưng vẫn trong `max_chars`. Context chung KHÔNG được dùng làm
`related_clause_ids` cho mâu thuẫn trừ khi chính nó cũng là quan hệ graph (FR-32 chỉ gồm cặp có cạnh).

Chỉ đọc masked text (INV-04). `ContextResolutionTrace` chỉ có ID + quan hệ + số ký tự (không text), dành
cho dev/eval (TDD-24), không persist và không trả cho người dùng.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence

from app.clause.graph_builder import ClauseGraph
from app.core.enums import ClauseEdgeType

COMMON_CONTEXT_LABELS = ("JOB_INFO", "CONTRACT_TERM")
GRAPH_RELATIONS = frozenset({"REFERS_TO", "REFERRED_BY", "PARENT", "CHILD", "PREV", "NEXT"})


@dataclass(frozen=True)
class ContextItem:
    clause_id: str
    relation: str  # REFERS_TO | REFERRED_BY | PARENT | CHILD | PREV | NEXT | COMMON_<LABEL>
    masked_text: str


@dataclass(frozen=True)
class ContextResolutionTrace:
    target_clause_id: str
    related: list[dict] = field(default_factory=list)  # [{clause_id, relation}] — không text
    included_in_risk_request: bool = True
    context_chars: int = 0
    truncated: bool = False

    def to_dict(self) -> dict:
        return {"target_clause_id": self.target_clause_id, "related": list(self.related),
                "included_in_risk_request": self.included_in_risk_request,
                "context_chars": self.context_chars, "truncated": self.truncated}


def _graph_order(graph: ClauseGraph, target: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    out += [(e.dst, "REFERS_TO") for e in graph.edges
            if e.edge_type == ClauseEdgeType.REFERS_TO and e.src == target]
    out += [(e.src, "REFERRED_BY") for e in graph.edges
            if e.edge_type == ClauseEdgeType.REFERS_TO and e.dst == target]
    parent = graph.parent_of(target)
    if parent:
        out.append((parent, "PARENT"))
    out += [(child, "CHILD") for child in graph.children_of(target)]
    prev, nxt = graph.prev_of(target), graph.next_of(target)
    if prev:
        out.append((prev, "PREV"))
    if nxt:
        out.append((nxt, "NEXT"))
    return out


def resolve_context(
    target: str,
    graph: Optional[ClauseGraph],
    masked_by_id: Mapping[str, str],
    labels_by_id: Mapping[str, Sequence[str]],
    *,
    max_related: int = 3,
    max_chars: int = 6000,
    common_labels: Sequence[str] = COMMON_CONTEXT_LABELS,
) -> tuple[list[ContextItem], ContextResolutionTrace]:
    """Trả (context theo thứ tự ưu tiên, trace). `graph=None` (CLAUSE_GRAPH_ENABLED=false) ⇒ không context."""
    if target not in masked_by_id:
        raise KeyError(target)
    if graph is None:
        return [], ContextResolutionTrace(target, included_in_risk_request=False)
    chosen: list[ContextItem] = []
    used = {target}
    chars = 0
    truncated = False

    def take(cid: str, relation: str) -> bool:
        nonlocal chars, truncated
        if cid in used or cid not in masked_by_id:
            return False
        text = masked_by_id[cid]
        if chars + len(text) > max_chars:
            truncated = True
            return False
        used.add(cid)
        chars += len(text)
        chosen.append(ContextItem(cid, relation, text))
        return True

    graph_count = 0
    for cid, relation in _graph_order(graph, target):
        if graph_count >= max_related:
            truncated = True
            break
        if take(cid, relation):
            graph_count += 1
    target_labels = set(labels_by_id.get(target, ()))
    for label in common_labels:
        if label in target_labels:
            continue  # target đã là clause chung của nhãn này
        if any(label in labels_by_id.get(item.clause_id, ()) for item in chosen):
            continue
        for cid in masked_by_id:  # thứ tự văn bản (dict giữ thứ tự chèn)
            if label in labels_by_id.get(cid, ()) and take(cid, f"COMMON_{label}"):
                break
    trace = ContextResolutionTrace(
        target, [{"clause_id": i.clause_id, "relation": i.relation} for i in chosen],
        included_in_risk_request=True, context_chars=chars, truncated=truncated)
    return chosen, trace
