"""Privacy masking metrics for BRD 7.3 and SRS NFR-SEC-01."""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

HIGH_SENSITIVITY_TYPES = frozenset(
    {"NATIONAL_ID_OR_PASSPORT", "PHONE", "EMAIL", "BANK_ACCOUNT", "TAX_ID"}
)
STANDARD_SENSITIVITY_TYPES = frozenset(
    {
        "PERSON_NAME",
        "DATE_OF_BIRTH",
        "RESIDENTIAL_ADDRESS",
        "BUSINESS_ADDRESS",
        "LEGAL_ENTITY",
        "ID_ISSUE",
        "SIGNATURE",
    }
)
KNOWN_PII_TYPES = HIGH_SENSITIVITY_TYPES | STANDARD_SENSITIVITY_TYPES


@dataclass(frozen=True)
class PrivacySpan:
    """PII span over canonical text, using Unicode code-point offsets."""

    kind: str
    start: int
    end: int


@dataclass(frozen=True)
class PreserveSpan:
    """A gold field whose text must remain unchanged in the outgoing payload."""

    start: int
    end: int


@dataclass(frozen=True)
class PrivacyGroupMetric:
    gold_count: int
    masked_count: int
    recall: float | None
    threshold: float
    threshold_met: bool | None
    ci95_low: float | None = None
    ci95_high: float | None = None
    valid_replicate_count: int = 0
    bootstrap_cluster_count: int = 0
    ci95_reason: str | None = None


@dataclass(frozen=True)
class PrivacyMetricResult:
    high_sensitivity: PrivacyGroupMetric
    standard_sensitivity: PrivacyGroupMetric
    preserve_count: int
    preserved_count: int
    preserve_rate: float | None
    preserve_threshold: float
    preserve_threshold_met: bool | None
    preserve_rate_ci95_low: float | None = None
    preserve_rate_ci95_high: float | None = None
    preserve_valid_replicate_count: int = 0
    bootstrap_cluster_count: int = 0
    bootstrap_iterations: int = 1000
    preserve_bootstrap_cluster_count: int = 0
    preserve_ci95_reason: str | None = None

    def group(self, name: str) -> PrivacyGroupMetric:
        """Return a group by its stable result key."""
        if name not in {"high_sensitivity", "standard_sensitivity"}:
            raise ValueError(f"unknown privacy metric group: {name}")
        return getattr(self, name)


def _validate_span(span: PrivacySpan | PreserveSpan, *, text_length: int) -> None:
    if (
        isinstance(span.start, bool)
        or not isinstance(span.start, int)
        or isinstance(span.end, bool)
        or not isinstance(span.end, int)
        or span.start < 0
        or span.end <= span.start
        or span.end > text_length
    ):
        raise ValueError("span must be a non-empty in-bounds half-open range")


def _group_metric(
    gold: tuple[PrivacySpan, ...],
    predicted: tuple[PrivacySpan, ...],
    *,
    kinds: frozenset[str],
    threshold: float,
) -> PrivacyGroupMetric:
    selected = tuple(span for span in gold if span.kind in kinds)
    if not selected:
        return PrivacyGroupMetric(0, 0, None, threshold, None)

    masked_count = 0
    for gold_span in selected:
        covered = [
            (max(gold_span.start, pred.start), min(gold_span.end, pred.end))
            for pred in predicted
            if pred.start < gold_span.end and pred.end > gold_span.start
        ]
        covered.sort()
        cursor = gold_span.start
        for start, end in covered:
            if start > cursor:
                break
            cursor = max(cursor, end)
            if cursor >= gold_span.end:
                masked_count += 1
                break

    recall = masked_count / len(selected)
    return PrivacyGroupMetric(len(selected), masked_count, recall, threshold, recall >= threshold)


def evaluate_privacy(
    canonical_text: str,
    outgoing_payload: str,
    *,
    predicted_spans: Iterable[PrivacySpan],
    gold_pii_spans: Iterable[PrivacySpan],
    preserve_spans: Iterable[PreserveSpan],
) -> PrivacyMetricResult:
    """Measure full-span PII recall and preservation on the exact outgoing payload.

    A gold PII span counts as masked only when the union of predicted mask spans
    covers every code point in it and the outgoing payload differs over that
    span. Preserve spans count as retained only when their text is byte-for-code-
    point identical at the same offsets. Text itself is never returned.
    """
    if not isinstance(canonical_text, str) or not isinstance(outgoing_payload, str):
        raise ValueError("canonical_text and outgoing_payload must be strings")
    if unicodedata.normalize("NFC", canonical_text) != canonical_text:
        raise ValueError("canonical_text must use NFC normalization")
    if len(canonical_text) != len(outgoing_payload):
        raise ValueError("canonical text and outgoing payload length must match")

    predicted = tuple(predicted_spans)
    gold = tuple(gold_pii_spans)
    preserve = tuple(preserve_spans)
    for span in (*predicted, *gold):
        if not isinstance(span, PrivacySpan):
            raise ValueError("PII spans must be PrivacySpan values")
        _validate_span(span, text_length=len(canonical_text))
        if span.kind not in KNOWN_PII_TYPES:
            raise ValueError(f"unknown PII type: {span.kind}")
    for span in preserve:
        if not isinstance(span, PreserveSpan):
            raise ValueError("preserve spans must be PreserveSpan values")
        _validate_span(span, text_length=len(canonical_text))

    effective_predicted = tuple(
        span
        for span in predicted
        if canonical_text[span.start : span.end] != outgoing_payload[span.start : span.end]
    )
    high = _group_metric(
        gold, effective_predicted, kinds=HIGH_SENSITIVITY_TYPES, threshold=0.99
    )
    standard = _group_metric(
        gold, effective_predicted, kinds=STANDARD_SENSITIVITY_TYPES, threshold=0.90
    )
    preserved_count = sum(
        canonical_text[span.start : span.end] == outgoing_payload[span.start : span.end]
        for span in preserve
    )
    preserve_rate = preserved_count / len(preserve) if preserve else None
    preserve_threshold = 0.95
    return PrivacyMetricResult(
        high_sensitivity=high,
        standard_sensitivity=standard,
        preserve_count=len(preserve),
        preserved_count=preserved_count,
        preserve_rate=preserve_rate,
        preserve_threshold=preserve_threshold,
        preserve_threshold_met=(
            preserve_rate >= preserve_threshold if preserve_rate is not None else None
        ),
    )
