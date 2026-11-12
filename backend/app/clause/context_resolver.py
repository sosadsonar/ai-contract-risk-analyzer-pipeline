"""Source-only Clause Graph context selection for a risk prompt."""

from dataclasses import dataclass
from typing import Mapping

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

    def to_dict(self) -> dict:
        return {
            "target_clause_id": self.target_clause_id,
            "related": [{"clause_id": cid, "relation": relation}
                        for cid, relation in self.related],
            "included_in_risk_request": self.included_in_risk_request,
            "context_chars": self.context_chars,
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
