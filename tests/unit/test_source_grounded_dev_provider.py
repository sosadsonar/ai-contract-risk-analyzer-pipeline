"""The local Dev provider emits schema-valid, source-derived risk candidates."""

import asyncio
import json

from app.ai.source_grounded_dev_provider import SourceGroundedDevProvider


class FixedClauseModel:
    def predict(self, texts):
        return tuple(("EMPLOYEE_OBLIGATIONS_DISCIPLINE",) for _ in texts)


def _call(provider, request):
    return asyncio.run(provider.generate_structured(
        model_id="local-dev", messages=[{}, {"content": json.dumps(request)}],
        response_schema={}, timeout_s=5)).data


def test_local_clause_labels_and_two_role_article17_citation_guard():
    provider = SourceGroundedDevProvider(FixedClauseModel())
    clause = _call(provider, {"schema_version": "clause_classification_request_v1",
                              "items": [{"clause_id": "cl_0001", "masked_text": "Công việc."}]})
    assert clause == {"items": [{"clause_id": "cl_0001",
                                 "clause_labels": ["EMPLOYEE_OBLIGATIONS_DISCIPLINE"]}]}
    text = "Người lao động phải đặt cọc 5.000.000 đồng để bảo đảm thực hiện hợp đồng."
    item = {"clause_id": "cl_0001", "masked_text": text,
            "candidate_ids": ["BLLD2019:art17:cl2"]}
    for role in ("EMPLOYEE", "EMPLOYER"):
        result = _call(provider, {"schema_version": "risk_analysis_request_v2",
                                  "role": role, "items": [item]})
        assert result["items"][0]["risk_labels"] == ["DEPOSIT_DOCUMENT_HELD"]
        assert result["items"][0]["citation_ids"] == ["BLLD2019:art17:cl2"]
        assert result["items"][0]["evidence_status"] == "SUPPORTED"
    item["candidate_ids"] = []
    result = _call(provider, {"schema_version": "risk_analysis_request_v2",
                              "role": "EMPLOYEE", "items": [item]})
    assert result["items"][0]["citation_ids"] == []
    assert result["items"][0]["evidence_status"] == "INSUFFICIENT_EVIDENCE"


def test_local_provider_does_not_emit_on_benign_source():
    provider = SourceGroundedDevProvider(FixedClauseModel())
    result = _call(provider, {"schema_version": "risk_analysis_request_v2",
                              "role": "EMPLOYEE", "items": [{
                                  "clause_id": "cl_0001",
                                  "masked_text": "Hai bên thực hiện hợp đồng theo pháp luật.",
                                  "candidate_ids": []}]})
    assert result == {"schema_version": "risk_output_v2", "items": []}


def test_original_document_uses_article_17_clause_1_and_review_explanation():
    provider = SourceGroundedDevProvider(FixedClauseModel())
    text = "Người lao động phải giao bản gốc bằng tốt nghiệp để công ty giữ đến khi hết hợp đồng."
    result = _call(provider, {
        "schema_version": "risk_analysis_request_v2", "role": "EMPLOYEE",
        "items": [{"clause_id": "cl_0001", "masked_text": text,
                   "candidate_ids": ["BLLD2019:art17:cl1"]}],
    })
    assert result["items"][0]["citation_ids"] == ["BLLD2019:art17:cl1"]
    assert result["items"][0]["explanation"] == (
        "Dấu hiệu giữ giấy tờ gốc hoặc yêu cầu bảo đảm khi thực hiện hợp đồng; "
        "cần người rà nguồn và điều luật."
    )


def test_same_basis_rules_keep_both_labels_in_one_clause_item():
    provider = SourceGroundedDevProvider(FixedClauseModel())
    text = ("Người lao động phải chấp nhận mọi sự điều động khi có yêu cầu của công ty; "
            "phụ cấp theo quy định công ty.")
    request = {"schema_version": "risk_analysis_request_v2", "role": "EMPLOYEE",
               "items": [{"clause_id": "cl_0001", "masked_text": text,
                          "candidate_ids": ["BLLD2019:art21:cl1:ptc",
                                            "BLLD2019:art21:cl1:ptđ"]}]}
    result = _call(provider, request)
    assert len(result["items"]) == 1
    assert set(result["items"][0]["risk_labels"]) == {
        "UNILATERAL_CHANGE", "BONUS_BENEFITS"}
