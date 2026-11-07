"""M4 exact quote span scoring using Python Unicode code-point offsets."""

from dataclasses import dataclass
from typing import Iterable

from ai_pipeline.evaluation.metrics.bootstrap import bootstrap_cluster_interval


@dataclass(frozen=True)
class QuoteSpanCase:
    source_text: str
    quote_text: str
    start_char: int | None
    end_char: int | None
    document_id: str = "UNSPECIFIED"
    offset_quality: str = "EXACT"


@dataclass(frozen=True)
class QuoteSpanResult:
    valid: int
    total: int
    rate: float | None
    excluded_context: int
    rate_ci95_low: float | None = None
    rate_ci95_high: float | None = None
    bootstrap_cluster_count: int = 0
    bootstrap_iterations: int = 1000
    bootstrap_valid_replicate_count: int = 0
    rate_ci95_reason: str | None = None


def evaluate_quote_spans(cases: Iterable[QuoteSpanCase]) -> QuoteSpanResult:
    valid = total = excluded_context = 0
    clusters: dict[str, list[QuoteSpanCase]] = {}
    for case in cases:
        if not isinstance(case.document_id, str) or not case.document_id.strip():
            raise ValueError("document_id must be non-empty")
        clusters.setdefault(case.document_id, []).append(case)
        if case.offset_quality not in {"EXACT", "CONTEXT"}:
            raise ValueError("offset_quality must be EXACT or CONTEXT")
        if case.offset_quality == "CONTEXT":
            excluded_context += 1
            continue
        total += 1
        start, end = case.start_char, case.end_char
        if (
            isinstance(start, int) and not isinstance(start, bool)
            and isinstance(end, int) and not isinstance(end, bool)
            and 0 <= start < end <= len(case.source_text)
            and bool(case.quote_text)
            and case.source_text[start:end] == case.quote_text
        ):
            valid += 1
    interval = bootstrap_cluster_interval(
        {
            key: tuple(value)
            for key, value in clusters.items()
            if any(case.offset_quality == "EXACT" for case in value)
        },
        lambda sampled: (
            sum(_is_valid(case) for case in sampled if case.offset_quality == "EXACT")
            / sum(case.offset_quality == "EXACT" for case in sampled)
            if any(case.offset_quality == "EXACT" for case in sampled) else None
        ),
    )
    return QuoteSpanResult(
        valid, total, valid / total if total else None, excluded_context,
        interval.low, interval.high, interval.cluster_count, interval.iterations,
        interval.valid_replicate_count,
        (
            "fewer than two contributing independent document clusters"
            if interval.low is None and interval.cluster_count < 2
            else "fewer than two valid bootstrap replicates"
            if interval.low is None and interval.valid_replicate_count < 2
            else None
        ),
    )


def _is_valid(case: QuoteSpanCase) -> bool:
    start, end = case.start_char, case.end_char
    return (
        isinstance(start, int) and not isinstance(start, bool)
        and isinstance(end, int) and not isinstance(end, bool)
        and 0 <= start < end <= len(case.source_text)
        and bool(case.quote_text)
        and case.source_text[start:end] == case.quote_text
    )
