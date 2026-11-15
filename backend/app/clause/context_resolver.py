"""Context Resolver cho Risk LLM (TDD §12.2–12.3, C-14 b, X-21 / FR-33).

* `resolve_context(graph, target_id, masked_clauses)` — ngữ cảnh graph theo thứ tự TDD §12.2: REFERS_TO đi
  ra, REFERS_TO đi vào, cha, con, clause trước, clause sau; khử trùng, tối đa `max_related` clause và
  `max_context_chars` code point. API của Data Lead, dùng cho đo M8/M2 Dev (giữ nguyên hành vi).
* `resolve_risk_context(...)` — dùng ở `app.pipeline`: gọi `resolve_context` rồi thêm ngữ cảnh chung FR-33
  (clause đầu tiên có nhãn JOB_INFO và CONTRACT_TERM; SRS gọi là CONTRACT_TERM_TYPE), mỗi nhãn tối đa một
  clause, không tính vào `max_related` nhưng vẫn trong `max_context_chars`. Relation `COMMON_<LABEL>` KHÔNG
  được dùng làm `related_clause_ids` (FR-32 chỉ gồm cặp có cạnh Clause Graph).

Chỉ đọc masked text (INV-04). `ContextResolutionTrace` chỉ có ID, quan hệ và số ký tự (TDD-24).
"""

from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

from app.clause.graph_builder import ClauseGraph
from app.clause.segmenter import SegmentationResult
from app.core.enums import ClauseEdgeType


@dataclass(frozen=True)
class ContextClause:
    clause_id: str
    relation: str
    masked_text: str


@dataclass(frozen=True)
class ContextResolutionTrace:
    target_clause_id: str
    related: tuple[tuple[str, str], ...]
    included_in_risk_request: bool
    context_chars: int
    truncated: bool = False

    def to_dict(self) -> dict:
        return {
            "target_clause_id": self.target_clause_id,
            "related": [{"clause_id": cid, "relation": relation}
                        for cid, relation in self.related],
            "included_in_risk_request": self.included_in_risk_request,
            "context_chars": self.context_chars,
            "truncated": self.truncated,
        }


def build_masked_clause_map(segmentation: SegmentationResult, masked_text: str) -> dict[str, str]:
    """Keep every graph node, including ineligible parents, using only masked slices."""
    result: dict[str, str] = {}
    for clause in segmentation.clauses:
        if not (0 <= clause.start_char < clause.end_char <= len(masked_text)):
            raise ValueError("invalid masked clause span")
        if clause.clause_id in result:
            raise ValueError("duplicate clause id")
        result[clause.clause_id] = masked_text[clause.start_char:clause.end_char]
    return result


def resolve_context(
    graph: ClauseGraph,
    target_id: str,
    masked_clauses: Mapping[str, str],
    *,
    max_related: int = 3,
    max_context_chars: int = 6000,
) -> list[ContextClause]:
    """TDD §12.2 priority; include no source text outside the masked mapping."""
    if target_id not in graph.node_ids or target_id not in masked_clauses:
        raise ValueError("unknown target clause")
    if max_related < 0 or max_context_chars < 0:
        raise ValueError("negative context limit")
    if max_related == 0 or max_context_chars == 0:
        return []
    ordered: list[tuple[str, str]] = []
    ordered.extend((e.dst, "REFERS_TO") for e in graph.edges
                   if e.edge_type == ClauseEdgeType.REFERS_TO and e.src == target_id)
    ordered.extend((e.src, "REFERRED_BY") for e in graph.edges
                   if e.edge_type == ClauseEdgeType.REFERS_TO and e.dst == target_id)
    parent = graph.parent_of(target_id)
    if parent:
        ordered.append((parent, "PARENT_OF"))
    ordered.extend((child, "CHILD_OF") for child in graph.children_of(target_id))
    previous = graph.prev_of(target_id)
    following = graph.next_of(target_id)
    if previous:
        ordered.append((previous, "PREVIOUS"))
    if following:
        ordered.append((following, "NEXT"))
    result: list[ContextClause] = []
    seen = {target_id}
    used = 0
    for clause_id, relation in ordered:
        if clause_id in seen or clause_id not in masked_clauses:
            continue
        seen.add(clause_id)
        masked_text = masked_clauses[clause_id]
        if not isinstance(masked_text, str):
            raise ValueError("masked clause text must be a string")
        if used + len(masked_text) > max_context_chars:
            continue
        result.append(ContextClause(clause_id, relation, masked_text))
        used += len(masked_text)
        if len(result) >= max_related:
            break
    return result


COMMON_CONTEXT_LABELS = ("JOB_INFO", "CONTRACT_TERM")
COMMON_PREFIX = "COMMON_"
# Backward-compatible alias (bản W5 của pipeline dùng tên này).
ContextItem = ContextClause


def resolve_risk_context(
    target_id: str,
    graph: Optional[ClauseGraph],
    masked_clauses: Mapping[str, str],
    labels_by_id: Mapping[str, Sequence[str]],
    *,
    max_related: int = 3,
    max_context_chars: int = 6000,
    common_labels: Sequence[str] = COMMON_CONTEXT_LABELS,
) -> tuple[list[ContextClause], ContextResolutionTrace]:
    """Ngữ cảnh graph (`resolve_context`) + ngữ cảnh chung FR-33. `graph=None` ⇒ không ngữ cảnh."""
    if target_id not in masked_clauses:
        raise ValueError("unknown target clause")
    if graph is None:
        return [], ContextResolutionTrace(target_id, (), False, 0)
    chosen = resolve_context(graph, target_id, masked_clauses, max_related=max_related,
                             max_context_chars=max_context_chars)
    used = sum(len(c.masked_text) for c in chosen)
    seen = {target_id, *(c.clause_id for c in chosen)}
    neighbors = {e.dst if e.src == target_id else e.src for e in graph.edges
                 if target_id in (e.src, e.dst)} & set(masked_clauses)
    truncated = len(chosen) < len(neighbors - {target_id})  # bị cắt bởi max_related / max_context_chars
    target_labels = set(labels_by_id.get(target_id, ()))
    for label in common_labels:
        if label in target_labels or any(label in labels_by_id.get(c.clause_id, ()) for c in chosen):
            continue
        for clause_id, text in masked_clauses.items():  # thứ tự văn bản
            if clause_id in seen or label not in labels_by_id.get(clause_id, ()):
                continue
            if used + len(text) > max_context_chars:
                truncated = True
                break
            chosen.append(ContextClause(clause_id, f"{COMMON_PREFIX}{label}", text))
            seen.add(clause_id)
            used += len(text)
            break
    trace = ContextResolutionTrace(target_id, tuple((c.clause_id, c.relation) for c in chosen),
                                   True, used, truncated)
    return chosen, trace
