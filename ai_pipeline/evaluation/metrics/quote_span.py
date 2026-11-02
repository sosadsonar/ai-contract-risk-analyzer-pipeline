"""M4 exact quote span scoring using Python Unicode code-point offsets."""

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class QuoteSpanCase:
    source_text: str
    quote_text: str
    start_char: int | None
    end_char: int | None
    offset_quality: str = "EXACT"


@dataclass(frozen=True)
class QuoteSpanResult:
    valid: int
    total: int
    rate: float | None
    excluded_context: int


def evaluate_quote_spans(cases: Iterable[QuoteSpanCase]) -> QuoteSpanResult:
    valid = total = excluded_context = 0
    for case in cases:
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
    return QuoteSpanResult(valid, total, valid / total if total else None, excluded_context)
