from datetime import date

import pytest
from app.legal.corpus_loader import LegalCorpus, LegalProvision

from ai_pipeline.evaluation.metrics.citation_validity import CitationCheck, evaluate_citation_validity
from ai_pipeline.evaluation.metrics.injected_recall import (
    InjectedErrorCase,
    RiskPrediction,
    evaluate_injected_recall,
)
from ai_pipeline.evaluation.metrics.quote_span import QuoteSpanCase, evaluate_quote_spans


@pytest.fixture
def corpus():
    provisions = (
        LegalProvision("LAW:art1", "LAW", "Fixture Law", "v1", "1", None, None,
                       ("LAW", "1"), "Active text", date(2021, 1, 1), None),
        LegalProvision("LAW:art2", "LAW", "Fixture Law", "v1", "2", None, None,
                       ("LAW", "2"), "Expired text", date(2020, 1, 1), date(2022, 12, 31)),
    )
    return LegalCorpus("fixture", "fixture_graph", "Asia/Ho_Chi_Minh", "APPROVED", provisions, (), {})


def test_m3a_requires_candidate_corpus_presence_and_effectivity(corpus):
    checks = (
        CitationCheck("LAW:art1", ("LAW:art1",)),
        CitationCheck("LAW:art1", ("LAW:art2",)),
        CitationCheck("LAW:art999", ("LAW:art999",)),
        CitationCheck("LAW:art2", ("LAW:art2",)),
    )

    result = evaluate_citation_validity(checks, corpus, as_of=date(2025, 1, 1))

    assert (result.total, result.valid, result.rate) == (4, 1, 0.25)
    assert (result.in_candidate_count, result.in_corpus_count, result.effective_count) == (3, 3, 2)


def test_m3a_empty_citation_set_has_undefined_rate(corpus):
    result = evaluate_citation_validity((), corpus, as_of=date(2025, 1, 1))

    assert result.total == result.valid == 0
    assert result.rate is None


def test_m3a_rejects_datetime_analysis_date(corpus):
    with pytest.raises(ValueError, match="as_of must be a date"):
        evaluate_citation_validity((), corpus, as_of=__import__("datetime").datetime(2025, 1, 1))


def test_m4_checks_exact_substring_and_half_open_codepoint_offsets():
    text = "A😀lương 5 triệu"
    cases = (
        QuoteSpanCase(text, "😀lương", 1, 7),
        QuoteSpanCase(text, "lương", 2, 6),
        QuoteSpanCase(text, "sai", 0, 3),
        QuoteSpanCase(text, "😀", 1, 2),
    )

    result = evaluate_quote_spans(cases)

    assert (result.valid, result.total, result.rate, result.excluded_context) == (2, 4, 0.5, 0)


def test_m4_excludes_context_gold_from_exact_span_denominator():
    cases = (
        QuoteSpanCase("Exact source", "Exact", 0, 5, offset_quality="EXACT"),
        QuoteSpanCase("Repeated source", "Repeated", None, None, offset_quality="CONTEXT"),
    )

    result = evaluate_quote_spans(cases)

    assert (result.valid, result.total, result.rate, result.excluded_context) == (1, 1, 1.0, 1)


def test_m4_returns_undefined_when_all_spans_are_context():
    result = evaluate_quote_spans((
        QuoteSpanCase("Context", "Context", None, None, offset_quality="CONTEXT"),
    ))

    assert result.rate is None
    assert result.total == 0
    assert result.excluded_context == 1


def test_m4_rejects_unknown_offset_quality():
    with pytest.raises(ValueError, match="offset_quality must be EXACT or CONTEXT"):
        evaluate_quote_spans((QuoteSpanCase("text", "text", 0, 4, offset_quality="UNKNOWN"),))


def test_m5_requires_exact_clause_role_and_label_and_caps_duplicate_predictions():
    gold = (
        InjectedErrorCase("i1", "clause-a", "EMPLOYEE", "WAGE"),
        InjectedErrorCase("i2", "clause-b", "EMPLOYER", "TERMINATION"),
    )
    predictions = (
        RiskPrediction("clause-a", "EMPLOYEE", "WAGE"),
        RiskPrediction("clause-b", "EMPLOYEE", "TERMINATION"),
        RiskPrediction("clause-a", "EMPLOYEE", "WAGE"),
    )

    result = evaluate_injected_recall(gold, predictions)

    assert (result.hits, result.total, result.recall) == (1, 2, 0.5)
    assert result.missed_injection_ids == ("i2",)


def test_m5_empty_gold_has_undefined_recall():
    result = evaluate_injected_recall((), ())

    assert result.total == result.hits == 0
    assert result.recall is None


def test_m5_rejects_duplicate_injection_ids():
    case = InjectedErrorCase("i1", "clause-a", "EMPLOYEE", "WAGE")
    with pytest.raises(ValueError, match="injection IDs must be unique"):
        evaluate_injected_recall((case, case), ())
