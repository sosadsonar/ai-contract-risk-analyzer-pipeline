"""Fail-fast rules for legal citations, versions and graph edges (SRS FR-24/30)."""

import math
import unicodedata
from collections import defaultdict

from app.clause.taxonomy import CLAUSE_LABEL_SET
from app.domain.errors import LegalCorpusConflict
from app.legal.citation_id import make_citation_id
from app.legal.corpus_loader import LegalCorpus, LegalProvision


def _fail(message: str) -> None:
    raise LegalCorpusConflict(message)


def _validate_provision(p: LegalProvision) -> None:
    try:
        expected = make_citation_id(p.document_id, p.article, p.clause, p.point)
    except ValueError as exc:
        _fail(f"{p.citation_id}: {exc}")
    if p.citation_id != expected:
        _fail(f"{p.citation_id}: expected deterministic citation_id {expected}")
    if not all(isinstance(x, str) and x.strip() for x in (p.document_name, p.version, p.content)):
        _fail(f"{p.citation_id}: missing text/version metadata")
    if unicodedata.normalize("NFC", p.content) != p.content:
        _fail(f"{p.citation_id}: content must be NFC")
    expected_path = tuple(expected.split(":"))
    if p.parent_path != expected_path:
        _fail(f"{p.citation_id}: noncanonical parent_path")
    if p.effective_from is None or (p.effective_to is not None and p.effective_to < p.effective_from):
        _fail(f"{p.citation_id}: invalid effective dates")


def _validate_versions(provisions: tuple[LegalProvision, ...]) -> None:
    grouped = defaultdict(list)
    for p in provisions:
        grouped[p.citation_id].append(p)
    for cid, versions in grouped.items():
        versions.sort(key=lambda p: p.effective_from)
        for older, newer in zip(versions, versions[1:]):
            # effective_to means last valid date (inclusive).
            if older.effective_to is None or older.effective_to >= newer.effective_from:
                _fail(f"{cid}: overlapping versions")


def _validate_edges(corpus: LegalCorpus) -> None:
    nodes = {p.citation_id for p in corpus.provisions}
    parents: dict[str, set[str]] = defaultdict(set)
    for p in corpus.provisions:
        parent = ":".join(p.parent_path[:-1])
        if parent in nodes:
            parents[parent].add(p.citation_id)
    seen_edges = set()
    for edge in corpus.edges:
        if edge.edge_type not in {"REFERS_TO", "GUIDES"} or edge.origin != "MANUAL":
            _fail("edges.jsonl: only verified MANUAL REFERS_TO/GUIDES are allowed")
        if edge.from_citation_id not in nodes or edge.to_citation_id not in nodes:
            _fail("edges.jsonl: unknown citation endpoint")
        if edge.from_citation_id == edge.to_citation_id:
            _fail("edges.jsonl: self-loop")
        key = (edge.from_citation_id, edge.to_citation_id, edge.edge_type)
        if key in seen_edges:
            _fail("edges.jsonl: duplicate edge")
        seen_edges.add(key)
    # Structural PARENT_OF edges are derived from canonical parent_path only.
    active, finished = set(), set()

    def visit(node: str) -> None:
        if node in active:
            _fail("PARENT_OF cycle detected")
        if node in finished:
            return
        active.add(node)
        for child in parents[node]:
            visit(child)
        active.remove(node)
        finished.add(node)

    for node in nodes:
        visit(node)


def validate_corpus(corpus: LegalCorpus) -> None:
    """Validate metadata and all records before opening a retriever."""
    if corpus.release_status not in ("DRAFT", "APPROVED"):
        _fail("manifest.yaml: invalid release_status")
    if not all(isinstance(v, str) and v.strip() for v in (
        corpus.corpus_version, corpus.graph_version, corpus.timezone,
    )):
        _fail("manifest.yaml: empty version/timezone")
    if corpus.timezone != "Asia/Ho_Chi_Minh":
        _fail("manifest.yaml: expected Asia/Ho_Chi_Minh")
    if not corpus.provisions:
        _fail("provisions.jsonl: corpus cannot be empty")
    for p in corpus.provisions:
        _validate_provision(p)
    _validate_versions(corpus.provisions)
    known = {p.citation_id for p in corpus.provisions}
    if not isinstance(corpus.label_map, dict) or not corpus.label_map:
        _fail("label_map.yaml: empty or invalid mapping")
    for label, weights in corpus.label_map.items():
        if label not in CLAUSE_LABEL_SET or not isinstance(weights, dict):
            _fail(f"label_map.yaml: unknown label {label}")
        for cid, weight in weights.items():
            if cid not in known or isinstance(weight, bool) or not isinstance(weight, (int, float)):
                _fail(f"label_map.yaml: unknown ID or invalid weight for {label}/{cid}")
            if not math.isfinite(weight) or not 0 <= weight <= 1:
                _fail(f"label_map.yaml: weight outside 0..1 for {label}/{cid}")
    _validate_edges(corpus)
