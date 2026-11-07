import json
from pathlib import Path

import pytest
from app.privacy.masker import mask

from ai_pipeline.evaluation.metrics.privacy import (
    PreserveSpan,
    PrivacySpan,
    evaluate_privacy,
)

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "privacy"


def _span(text: str, value: str, kind: str) -> PrivacySpan:
    start = text.index(value)
    return PrivacySpan(kind=kind, start=start, end=start + len(value))


def _preserve(text: str, value: str) -> PreserveSpan:
    start = text.index(value)
    return PreserveSpan(start=start, end=start + len(value))


def test_privacy_metric_reports_group_recall_and_preserve_rate():
    canonical = "CCCD 079203012345 phone 0912345678 name Nguyen Van An salary 10m"
    id_span = _span(canonical, "079203012345", "NATIONAL_ID_OR_PASSPORT")
    phone_span = _span(canonical, "0912345678", "PHONE")
    name_span = _span(canonical, "Nguyen Van An", "PERSON_NAME")
    salary = _preserve(canonical, "salary 10m")
    masked = list(canonical)
    for span in (id_span, phone_span):
        masked[span.start : span.end] = "*" * (span.end - span.start)

    result = evaluate_privacy(
        canonical,
        "".join(masked),
        predicted_spans=(id_span, phone_span),
        gold_pii_spans=(id_span, phone_span, name_span),
        preserve_spans=(salary,),
    )

    high = result.group("high_sensitivity")
    standard = result.group("standard_sensitivity")
    assert (high.gold_count, high.masked_count, high.recall, high.threshold) == (
        2,
        2,
        1.0,
        0.99,
    )
    assert (standard.gold_count, standard.masked_count, standard.recall, standard.threshold) == (
        1,
        0,
        0.0,
        0.90,
    )
    assert result.preserve_rate == 1.0
    assert result.preserve_threshold == 0.95


def test_privacy_metric_requires_full_gold_span_coverage():
    canonical = "Email an@example.com"
    gold = _span(canonical, "an@example.com", "EMAIL")
    partial = PrivacySpan(kind="EMAIL", start=gold.start, end=gold.end - 1)
    masked = canonical[: partial.start] + "*" * (partial.end - partial.start) + canonical[partial.end :]

    result = evaluate_privacy(
        canonical,
        masked,
        predicted_spans=(partial,),
        gold_pii_spans=(gold,),
        preserve_spans=(),
    )

    assert result.group("high_sensitivity").masked_count == 0
    assert result.group("high_sensitivity").recall == 0.0
    assert result.preserve_rate is None


def test_privacy_metric_rejects_invalid_offsets_and_length_mismatch():
    canonical = "Email x@y.com"
    invalid = PrivacySpan(kind="EMAIL", start=7, end=6)

    try:
        evaluate_privacy(
            canonical,
            canonical,
            predicted_spans=(),
            gold_pii_spans=(invalid,),
            preserve_spans=(),
        )
    except ValueError as exc:
        assert "span" in str(exc)
    else:
        raise AssertionError("invalid span must fail")

    try:
        evaluate_privacy(
            canonical,
            canonical + "!",
            predicted_spans=(),
            gold_pii_spans=(),
            preserve_spans=(),
        )
    except ValueError as exc:
        assert "length" in str(exc)
    else:
        raise AssertionError("payload length mismatch must fail")


def test_privacy_metric_does_not_score_empty_pii_group_as_perfect():
    result = evaluate_privacy(
        "No annotated PII",
        "No annotated PII",
        predicted_spans=(),
        gold_pii_spans=(),
        preserve_spans=(),
    )

    assert result.group("high_sensitivity").recall is None
    assert result.group("standard_sensitivity").recall is None
    assert result.preserve_rate is None


def test_privacy_metric_does_not_count_spans_absent_from_outgoing_payload():
    canonical = "Email an@example.com"
    gold = _span(canonical, "an@example.com", "EMAIL")

    result = evaluate_privacy(
        canonical,
        canonical,
        predicted_spans=(gold,),
        gold_pii_spans=(gold,),
        preserve_spans=(),
    )

    assert result.group("high_sensitivity").masked_count == 0


def test_privacy_metric_rejects_non_nfc_canonical_text():
    with pytest.raises(ValueError, match="NFC"):
        evaluate_privacy(
            "e\u0301",
            "e\u0301",
            predicted_spans=(),
            gold_pii_spans=(),
            preserve_spans=(),
        )


def test_privacy_metric_runs_against_repository_masker_fixture():
    case = json.loads((FIXTURE_DIR / "case_001.json").read_text(encoding="utf-8"))
    masked = mask(case["canonical_text"])
    gold = tuple(
        PrivacySpan(kind=row["type"], start=row["start"], end=row["end"])
        for row in case["pii_spans"]
    )
    predicted = tuple(
        PrivacySpan(kind=span.type.value, start=span.start, end=span.end)
        for span in masked.pii_spans
    )
    preserve = tuple(
        PreserveSpan(start=row["start"], end=row["end"])
        for row in case["preserve_spans"]
    )

    result = evaluate_privacy(
        case["canonical_text"],
        masked.masked_text,
        predicted_spans=predicted,
        gold_pii_spans=gold,
        preserve_spans=preserve,
    )

    assert result.group("high_sensitivity").gold_count == 4
    assert result.group("standard_sensitivity").gold_count == 7
    assert result.preserve_count > 0
    assert 0 <= result.preserve_rate <= 1
