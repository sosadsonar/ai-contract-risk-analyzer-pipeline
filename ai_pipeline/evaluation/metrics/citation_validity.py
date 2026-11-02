"""M3a citation validity against retrieval candidates and dated corpus."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable

from app.legal.corpus_loader import LegalCorpus


@dataclass(frozen=True)
class CitationCheck:
    citation_id: str
    candidate_citation_ids: tuple[str, ...]


@dataclass(frozen=True)
class CitationValidityResult:
    total: int
    valid: int
    rate: float | None
    in_candidate_count: int
    in_corpus_count: int
    effective_count: int


def evaluate_citation_validity(
    checks: Iterable[CitationCheck], corpus: LegalCorpus, *, as_of: date
) -> CitationValidityResult:
    """Count citations that are candidates, present, and effective on ``as_of``."""
    if isinstance(as_of, datetime) or not isinstance(as_of, date):
        raise ValueError("as_of must be a date")

    items = tuple(checks)
    by_citation: dict[str, list] = {}
    for provision in corpus.provisions:
        by_citation.setdefault(provision.citation_id, []).append(provision)

    in_candidates = in_corpus = effective = valid = 0
    for check in items:
        candidate = check.citation_id in check.candidate_citation_ids
        versions = by_citation.get(check.citation_id, ())
        active = any(
            p.effective_from <= as_of and (p.effective_to is None or as_of <= p.effective_to)
            for p in versions
        )
        in_candidates += candidate
        in_corpus += bool(versions)
        effective += active
        valid += candidate and bool(versions) and active

    total = len(items)
    return CitationValidityResult(
        total, valid, valid / total if total else None, in_candidates, in_corpus, effective
    )
