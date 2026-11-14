"""C-15 (a): advice/unsupported-reference lint, sanitizer, citation validator, retry ngữ nghĩa (X-22)."""

import asyncio
import json
from datetime import date
from types import SimpleNamespace

import pytest
from app.ai.provider import InMemoryLedger, LLMResponse
from app.ai.risk_adapter import LegalCandidate, RelatedClause, RiskItemIn, RiskItemOut, analyze_risks
from app.domain.errors import AiOutputInvalid
from app.legal.corpus_loader import LegalCorpus, LegalProvision
from app.risk.citation_validator import effective_provisions, validate_citations
from app.risk.lint import (
    detect_advice,
    detect_unsupported_reference,
    lint_explanation,
    sanitize_explanation,
)

# ------------------------------------------------------------------ advice


@pytest.mark.parametrize("text", [
    "Bạn nên thương lượng lại mức lương.", "NLĐ nên yêu cầu bổ sung phụ cấp.", "Người lao động nên từ chối ký.",
    "Nên sửa điều khoản này.", "Đề nghị sửa thời gian thử việc.", "Khuyến nghị làm rõ mức thưởng.",
    "NSDLĐ nên bổ sung căn cứ.",
])
def test_advice_detected(text):
    assert detect_advice(text)


@pytest.mark.parametrize("text", [
    "Thời gian thử việc dài nên dẫn đến bất lợi cho người lao động.",
    "Vì không nêu mức cụ thể nên khó xác định quyền lợi.",
    "Điều khoản cho phép điều chuyển không cần báo trước.",
])
def test_bare_nen_is_not_advice(text):
    assert not detect_advice(text)


# ------------------------------------------------------------------ unsupported reference


def test_reference_must_match_selected_citation():
    assert not detect_unsupported_reference("Vượt mức tại Điều 25 Bộ luật Lao động 2019.", ["BLLD2019:art25:cl1"])
    assert detect_unsupported_reference("Trái Điều 97 Bộ luật Lao động 2019.", ["BLLD2019:art25:cl1"])
    assert detect_unsupported_reference("Trái Khoản 2 Điều 25 Bộ luật Lao động.", ["BLLD2019:art25:cl1"])
    assert detect_unsupported_reference("Trái quy định của Bộ luật Lao động.", [])
    assert not detect_unsupported_reference("Mâu thuẫn với điều khoản số 5 của hợp đồng.", [])
    assert not detect_unsupported_reference("Khác với Điều 5 của hợp đồng này.", [])


def test_sanitizer_drops_only_violating_sentences():
    text = "Thời gian thử việc vượt mức trong căn cứ. Bạn nên thương lượng lại. Trái Điều 97 Bộ luật Lao động."
    assert sanitize_explanation(text, ["BLLD2019:art25"]) == "Thời gian thử việc vượt mức trong căn cứ."
    assert sanitize_explanation("Bạn nên thương lượng lại.", []) is None
    assert lint_explanation(text, ["BLLD2019:art25"]) == ["advice", "unsupported_reference"]


# ------------------------------------------------------------------ citation validator


def _prov(cid, start, end=None):
    return LegalProvision(cid, "BLLD2019", "Bộ luật Lao động 2019", "45/2019/QH14", "25", None, None, (),
                          "nội dung", start, end)


CORPUS = LegalCorpus("c", "g", "Asia/Ho_Chi_Minh", "APPROVED",
                     (_prov("BLLD2019:art25", date(2021, 1, 1)), _prov("OLD:art1", date(2010, 1, 1), date(2015, 1, 1))),
                     (), {})


def _out(cid, cites, status="SUPPORTED"):
    return RiskItemOut(cid, "LEGAL_VIOLATION", ["PROBATION"], cites, status, "Giải thích đủ dài cho rủi ro.")


def test_citation_validator_filters_and_downgrades():
    eff = effective_provisions(CORPUS, date(2026, 11, 13))
    items = [_out("cl_0001", ["BLLD2019:art25", "X:art9"]),          # ngoài candidate bị lọc
             _out("cl_0002", ["OLD:art1"]),                           # hết hiệu lực ⇒ hạ INSUFFICIENT
             _out("cl_0003", [], "INSUFFICIENT_EVIDENCE")]
    cands = {"cl_0001": ["BLLD2019:art25"], "cl_0002": ["OLD:art1"], "cl_0003": []}
    out, stats = validate_citations(items, cands, eff)
    assert out[0].citation_ids == ["BLLD2019:art25"] and out[0].evidence_status == "SUPPORTED"
    assert out[1].citation_ids == [] and out[1].evidence_status == "INSUFFICIENT_EVIDENCE"
    assert (stats.outside_candidate, stats.not_effective, stats.downgraded_to_insufficient) == (1, 1, 1)


# ------------------------------------------------------------------ adapter semantic retry

CFG = SimpleNamespace(GEMINI_MODEL_ID="m", RISK_BATCH_SIZE=6, LLM_PARALLELISM=1, LLM_TIMEOUT_SECONDS=5,
                      LLM_AUTO_RETRY=1)
CANDS = {"BLLD2019:art25": LegalCandidate("BLLD2019:art25", "Thử việc...", "Bộ luật Lao động 2019", "25")}


class Seq:
    def __init__(self, *responses):
        self.responses, self.calls = list(responses), []

    async def generate_structured(self, *, model_id, messages, response_schema, timeout_s):
        self.calls.append(messages)
        return LLMResponse(self.responses[len(self.calls) - 1], model_id)


def _resp(**kw):
    item = {"clause_id": "cl_0001", "basis_type": "UNFAVORABLE", "risk_labels": ["PROBATION"],
            "citation_ids": ["BLLD2019:art25"], "evidence_status": "SUPPORTED",
            "explanation": "Thử việc ở mức tối đa trong căn cứ, bất lợi cho người lao động."}
    item.update(kw)
    return {"schema_version": "risk_output_v2", "items": [item]}


def _run(provider, role="EMPLOYEE", related=()):
    items = [RiskItemIn("cl_0001", "Thời gian thử việc 180 ngày.", ["CONTRACT_TERM"], ["BLLD2019:art25"],
                        list(related))]
    return asyncio.run(analyze_risks(role, items, CANDS, provider, InMemoryLedger(), CFG))


def test_invalid_combo_retried_with_feedback_then_accepted():
    p = Seq(_resp(basis_type="UNFAVORABLE", risk_labels=["SOCIAL_INSURANCE"]), _resp())
    out = _run(p)
    assert len(p.calls) == 2 and out.items[0].risk_labels == ["PROBATION"]
    feedback = p.calls[1][-1]["content"]
    assert "SOCIAL_INSURANCE" in feedback and "Thời gian thử việc" not in feedback  # không text hợp đồng


def test_invalid_combo_after_retry_becomes_needs_review():
    bad = _resp(basis_type="UNFAVORABLE", risk_labels=["SOCIAL_INSURANCE"])
    out = _run(Seq(bad, bad))
    it = out.items[0]
    assert it.need_review and it.evidence_status == "INSUFFICIENT_EVIDENCE" and it.citation_ids == []
    assert "need_review" not in it.to_dict()  # không lọt vào risk_output_v2


def test_advice_after_retry_is_sanitized_or_fails():
    advice = _resp(explanation="Thử việc ở mức tối đa trong căn cứ. Bạn nên thương lượng lại thời gian.")
    out = _run(Seq(advice, advice))
    assert out.items[0].explanation == "Thử việc ở mức tối đa trong căn cứ." and out.items[0].sanitized
    only_advice = _resp(explanation="Bạn nên thương lượng lại thời gian thử việc.")
    with pytest.raises(AiOutputInvalid):
        _run(Seq(only_advice, only_advice))


def test_related_ids_cannot_point_to_common_context():
    related = [RelatedClause("cl_0002", "COMMON_JOB_INFO", "Chức danh"), RelatedClause("cl_0003", "REFERS_TO", "x")]
    ok = _resp(basis_type="AMBIGUOUS", related_clause_ids=["cl_0003"])
    out = _run(Seq(ok), related=related)
    assert out.items[0].related_clause_ids == ["cl_0003"]
    bad = _resp(basis_type="AMBIGUOUS", related_clause_ids=["cl_0002"])
    with pytest.raises(AiOutputInvalid):
        _run(Seq(bad, bad), related=related)


def test_request_payload_contains_no_offsets():
    p = Seq(_resp())
    _run(p)
    req = json.loads(p.calls[0][1]["content"])
    assert "start_char" not in json.dumps(req) and req["role"] == "EMPLOYEE"
