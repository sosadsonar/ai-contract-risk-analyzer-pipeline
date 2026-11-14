"""The D1 smoke scorer must tolerate source-only classification filtering."""

from types import SimpleNamespace

from app.ai.clause_adapter import ClauseLabelItem, ClauseOutput

from ai_pipeline.evaluation.d1_clause_run import summarize
from ai_pipeline.evaluation.metrics.clause_classification import GoldSpan


def test_summarize_counts_all_segmentation_but_only_classified_predictions():
    clauses = [
        SimpleNamespace(clause_id="cl_0001", start_char=0, end_char=10),
        SimpleNamespace(clause_id="cl_0002", start_char=10, end_char=20),
    ]
    output = ClauseOutput(
        items=[ClauseLabelItem("cl_0002", ["OTHER"])],
        model_id="smoke",
        prompt_version="test",
        taxonomy_version="clause_taxonomy_v03",
    )
    run = SimpleNamespace(
        contract_id="HDLD001",
        canonical_len=20,
        pii_spans=0,
        segmentation=SimpleNamespace(clauses=clauses, warnings=[]),
        graph=SimpleNamespace(edges=[]),
        diagnostics=[],
        output=output,
    )

    report = summarize([run], {"HDLD001": ("x" * 20, [GoldSpan(10, 20, "OTHER")])}, measured=True)

    assert report["per_contract"][0]["clauses"] == 2
    assert report["per_contract"][0]["classified_clauses"] == 1
    assert report["m7_preliminary"]["pred_total"] == 1
