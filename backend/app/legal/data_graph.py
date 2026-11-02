"""One-hop legal graph index: canonical hierarchy and reviewer-verified edges.

C-13(a) builds adjacency only. C-13(b) ranking, caps and runtime fallback are
separate to keep the graph index auditable before it affects retrieval.
"""

from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import date, datetime
from typing import Any, Sequence

from app.domain.errors import LegalCorpusConflict
from app.legal.baseline_retriever import BaselineCandidate, BaselineRetriever
from app.legal.corpus_loader import LegalCorpus
from app.legal.corpus_validator import validate_corpus


@dataclass(frozen=True)
class GraphRelation:
    from_citation_id: str
    to_citation_id: str
    edge_type: str
    origin: str


@dataclass(frozen=True)
class GraphNeighbor:
    citation_id: str
    edge_type: str
    origin: str
    direction: str  # FORWARD = outgoing, REVERSE = incoming


class DataGraph:
    """Build from validated records; suggestions never enter the adjacency index."""

    def __init__(self, corpus: LegalCorpus, *, allow_draft: bool = False) -> None:
        validate_corpus(corpus)
        if corpus.release_status != "APPROVED" and not allow_draft:
            raise LegalCorpusConflict("data graph: corpus awaits Data/Legal reviewer sign-off")

        self._versions = defaultdict(list)
        for provision in corpus.provisions:
            self._versions[provision.citation_id].append(provision)
        citation_ids = set(self._versions)

        structural = set()
        for provision in corpus.provisions:
            parent = ":".join(provision.parent_path[:-1])
            if parent in citation_ids:
                structural.add(GraphRelation(parent, provision.citation_id, "PARENT_OF", "AUTO"))

        verified = {
            GraphRelation(edge.from_citation_id, edge.to_citation_id, edge.edge_type, edge.origin)
            for edge in corpus.edges
        }
        self.relations = tuple(sorted(
            structural | verified,
            key=lambda edge: (edge.from_citation_id, edge.to_citation_id, edge.edge_type),
        ))
        adjacency = defaultdict(list)
        for relation in self.relations:
            adjacency[relation.from_citation_id].append(GraphNeighbor(
                relation.to_citation_id, relation.edge_type, relation.origin, "FORWARD",
            ))
            adjacency[relation.to_citation_id].append(GraphNeighbor(
                relation.from_citation_id, relation.edge_type, relation.origin, "REVERSE",
            ))
        self._adjacency = {
            citation_id: tuple(sorted(neighbors, key=lambda n: (n.edge_type, n.citation_id, n.direction)))
            for citation_id, neighbors in adjacency.items()
        }

    def _active(self, citation_id: str, as_of: date) -> bool:
        return any(
            p.effective_from <= as_of and (p.effective_to is None or as_of <= p.effective_to)
            for p in self._versions.get(citation_id, ())
        )

    def neighbors(self, citation_id: str, *, as_of: date) -> tuple[GraphNeighbor, ...]:
        """Both traversal directions, restricted to effective endpoints at analysis date."""
        if not isinstance(as_of, date) or isinstance(as_of, datetime):
            raise ValueError("data graph: as_of must be a date")
        if not isinstance(citation_id, str) or not self._active(citation_id, as_of):
            return ()
        return tuple(
            item for item in self._adjacency.get(citation_id, ())
            if self._active(item.citation_id, as_of)
        )

    def expand(
        self,
        seeds: Sequence[BaselineCandidate],
        pool: Sequence[BaselineCandidate],
        cfg: Any,
        *,
        as_of: date,
    ) -> tuple[BaselineCandidate, ...]:
        """Expand one hop and merge graph candidates into a fixed-size pool."""
        final_k = cfg.RETRIEVAL_FINAL_K
        neighbor_cap = cfg.GRAPH_MAX_NEIGHBORS_PER_SEED
        child_cap = cfg.GRAPH_MAX_CHILDREN_PER_SEED
        caps = (final_k, neighbor_cap, child_cap)
        if any(isinstance(cap, bool) or not isinstance(cap, int) or cap < 1 for cap in caps):
            raise ValueError("data graph: retrieval and graph caps must be positive integers")
        pool_by_id = {item.citation_id: item for item in pool}
        seeds = tuple(seeds)
        if len(seeds) > final_k:
            raise ValueError("data graph: seeds cannot exceed retrieval final_k")
        if any(seed.citation_id not in pool_by_id for seed in seeds):
            raise ValueError("data graph: seed must be in baseline pool")
        seed_ids = {seed.citation_id for seed in seeds}
        graph_candidates: dict[str, tuple[float, BaselineCandidate]] = {}
        edge_bonus = {"REFERS_TO": 0.30, "GUIDES": 0.25, "PARENT_OF": 0.15}
        for seed in seeds:
            neighbors = list(self.neighbors(seed.citation_id, as_of=as_of))
            neighbors.sort(key=lambda n: (
                0 if (n.edge_type == "REFERS_TO" and n.direction == "FORWARD") else 1,
                -pool_by_id[n.citation_id].baseline_score if n.citation_id in pool_by_id else 0.0,
                n.citation_id,
            ))
            children = 0
            used = 0
            for neighbor in neighbors:
                if used >= neighbor_cap:
                    break
                if neighbor.citation_id in seed_ids:
                    continue
                candidate = pool_by_id.get(neighbor.citation_id)
                if candidate is None:
                    active = [
                        p for p in self._versions[neighbor.citation_id]
                        if p.effective_from <= as_of
                        and (p.effective_to is None or as_of <= p.effective_to)
                    ]
                    if len(active) != 1:
                        raise LegalCorpusConflict("data graph: ambiguous active neighbor version")
                    provision = active[0]
                    candidate = BaselineCandidate(
                        citation_id=provision.citation_id,
                        content=provision.content,
                        document_name=provision.document_name,
                        article=provision.article,
                        version=provision.version,
                        effective_from=provision.effective_from,
                        effective_to=provision.effective_to,
                        origin=f"GRAPH_{neighbor.edge_type}",
                        rank=0,
                        baseline_score=0.0,
                        bm25_normalized=0.0,
                    )
                if neighbor.edge_type == "PARENT_OF" and neighbor.direction == "FORWARD":
                    if children >= child_cap:
                        continue
                    children += 1
                used += 1
                direction_bonus = 0.05 if neighbor.direction == "FORWARD" else 0.0
                score = 0.60 * seed.baseline_score + edge_bonus[neighbor.edge_type] + direction_bonus
                prior = graph_candidates.get(candidate.citation_id)
                if prior is None or score > prior[0]:
                    graph_candidates[candidate.citation_id] = (score, candidate)
        backups = [
            item for item in pool
            if item.citation_id not in seed_ids and item.citation_id not in graph_candidates
        ]
        merged = [(item.baseline_score, item.citation_id, item) for item in backups]
        merged.extend((score, item.citation_id, item) for score, item in graph_candidates.values())
        merged.sort(key=lambda row: (-row[0], row[1]))
        result = tuple((*seeds, *(row[2] for row in merged[:final_k - len(seeds)])))
        return tuple(replace(item, rank=position) for position, item in enumerate(result, 1))


def get_candidates(
    retriever: BaselineRetriever,
    graph: DataGraph | None,
    masked_text: str,
    labels: Sequence[str],
    analysis_date: date,
    cfg: Any,
) -> tuple[tuple[BaselineCandidate, ...], bool]:
    """Retrieve a baseline pool, optionally graph-expand it, and safely fallback."""
    if cfg.RETRIEVAL_FINAL_K != retriever.final_k:
        raise ValueError("data graph: RETRIEVAL_FINAL_K must match baseline retriever")
    baseline = retriever.retrieve(masked_text, labels, as_of=analysis_date)
    if graph is None or not getattr(cfg, "DATA_GRAPH_ENABLED", True):
        return baseline.baseline_pool, False
    try:
        return graph.expand(baseline.seeds, baseline.baseline_pool, cfg, as_of=analysis_date), False
    except Exception:
        return baseline.baseline_pool, True
