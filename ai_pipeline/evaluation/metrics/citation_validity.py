"""M3a citation validity against retrieval candidates and dated corpus."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable

from app.legal.corpus_loader import LegalCorpus

from ai_pipeline.evaluation.metrics.bootstrap import bootstrap_cluster_interval


@dataclass(frozen=True)
class CitationCheck:
    citation_id: str
    candidate_citation_ids: tuple[str, ...]
    analysis_date: date | None = None
    source_document_id: str | None = None


@dataclass(frozen=True)
class CitationValidityResult:
    total: int
    valid: int
    rate: float | None
    in_candidate_count: int
    in_corpus_count: int
    effective_count: int
    rate_ci95_low: float | None = None
    rate_ci95_high: float | None = None
    bootstrap_cluster_count: int = 0
    bootstrap_iterations: int = 1000
    bootstrap_valid_replicate_count: int = 0


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
    clusters: dict[str, list[CitationCheck]] = {}
    for check in items:
        if not isinstance(check, CitationCheck):
            raise ValueError("each citation check must be a CitationCheck")
        if check.source_document_id is not None and (
            not isinstance(check.source_document_id, str) or not check.source_document_id.strip()
        ):
            raise ValueError("source_document_id must be non-empty when provided")
        cluster_id = check.source_document_id or "__unspecified__"
        clusters.setdefault(cluster_id, []).append(check)
        check_date = check.analysis_date if check.analysis_date is not None else as_of
        if isinstance(check_date, datetime) or not isinstance(check_date, date):
            raise ValueError("citation analysis_date must be a date")
        candidate = check.citation_id in check.candidate_citation_ids
        versions = by_citation.get(check.citation_id, ())
        active = any(
            p.effective_from <= check_date
            and (p.effective_to is None or check_date <= p.effective_to)
            for p in versions
        )
        in_candidates += candidate
        in_corpus += bool(versions)
        effective += active
        valid += candidate and bool(versions) and active

    total = len(items)
    interval = bootstrap_cluster_interval(
        {key: tuple(value) for key, value in clusters.items()},
        lambda sampled: (
            sum(
                check.citation_id in check.candidate_citation_ids
                and any(
                    provision.effective_from <= (check.analysis_date or as_of)
                    and (provision.effective_to is None or (check.analysis_date or as_of) <= provision.effective_to)
                    for provision in by_citation.get(check.citation_id, ())
                )
                for check in sampled
            ) / len(sampled)
            if sampled else None
        ),
    )
    return CitationValidityResult(
        total, valid, valid / total if total else None, in_candidates, in_corpus, effective,
        interval.low, interval.high, interval.cluster_count, interval.iterations,
        interval.valid_replicate_count,
    )
