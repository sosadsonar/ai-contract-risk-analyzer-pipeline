"""Dev-only dependency-injected pipeline, using synthetic text and fake providers."""

import asyncio
import json
from datetime import date
from types import SimpleNamespace

import pytest
from app.ai.provider import InMemoryLedger, LLMResponse
from app.ai.risk_adapter import LegalCandidate
from app.core.enums import Role, SessionStatus
from app.domain.errors import AiOutputInvalid
from app.legal.baseline_retriever import BaselineRetriever
from app.legal.corpus_loader import LegalCorpus, LegalProvision
from app.session.lock import ProcessingLease
from app.session.orchestrator import Orchestrator
from app.session.pipeline_runner import make_pipeline_runner, sanitize_advice_sentences
from app.session.store import InMemorySessionStore

SOURCE = (
    "Điều 1. Quy định chung:\n"
    "1.1 Người lao động Ông Nguyễn Văn An, CCCD: 001234567890 thực hiện công việc.\n"
    "Điều 2. Tiền lương:\n"
    "2.1 Tiền lương được áp dụng theo Điều 1 của Hợp đồng này."
)


def test_advice_sanitizer_keeps_non_advice_conjunction_unchanged():
    explanation = "Do quy định chưa rõ nên hai bên dễ tranh chấp."
    assert sanitize_advice_sentences(explanation) == (explanation, False)


@pytest.mark.parametrize("phrase", [
    "Người lao động nên thương lượng lại.",
    "NSDLĐ nên sửa điều khoản.",
    "Nên bổ sung thời hạn.",
    "Đề nghị sửa điều khoản.",
    "Khuyến nghị thay đổi cách tính.",
])
def test_advice_sanitizer_removes_only_advice_sentence(phrase):
    neutral = "Điều khoản chưa xác định thời hạn rõ ràng."
    assert sanitize_advice_sentences(neutral + " " + phrase) == (neutral, True)


def test_advice_sanitizer_fails_when_no_rationale_remains():
    with pytest.raises(AiOutputInvalid):
        sanitize_advice_sentences("Công ty nên sửa.")


class FakeProvider:
    def __init__(self, kind, citation_id=None):
        self.kind = kind
        self.citation_id = citation_id
        self.requests = []

    async def generate_structured(self, *, model_id, messages, response_schema, timeout_s):
        request = json.loads(messages[1]["content"])
        self.requests.append(request)
        if self.kind == "clause":
            data = {"items": [{"clause_id": item["clause_id"],
                               "clause_labels": ["COMPENSATION_BENEFITS"]}
                              for item in request["items"]]}
        else:
            data = {"schema_version": "risk_output_v2", "items": [
                {"clause_id": item["clause_id"], "basis_type": "LEGAL_VIOLATION",
                 "risk_labels": ["DEPOSIT_DOCUMENT_HELD"],
                 "citation_ids": [self.citation_id] if self.citation_id else [],
                 "evidence_status": "SUPPORTED" if self.citation_id else "INSUFFICIENT_EVIDENCE",
                 "explanation": ("Theo Điều 99, điều khoản có rủi ro cho người lao động."
                                 if self.citation_id == "OUTSIDE_CANDIDATE" else
                                 "Điều khoản chưa rõ điều kiện áp dụng cho vai trò đang xét.")}
                for item in request["items"]]}
        return LLMResponse(data, model_id)


def test_injected_runner_completes_with_masked_context_and_internal_reference():
    store, lease = InMemorySessionStore(), ProcessingLease()
    session = store.create(Role.EMPLOYEE)
    assert lease.try_acquire(session.session_id) == session.session_id
    clause, risk = FakeProvider("clause"), FakeProvider("risk")
    cfg = SimpleNamespace(GEMINI_MODEL_ID="fake-model", CLAUSE_BATCH_SIZE=20,
                          RISK_BATCH_SIZE=6, LLM_PARALLELISM=1,
                          LLM_TIMEOUT_SECONDS=5, LLM_AUTO_RETRY=0,
                          CLAUSE_GRAPH_MAX_RELATED=3, CLAUSE_GRAPH_MAX_CONTEXT_CHARS=6000)
    runner = make_pipeline_runner(SOURCE, clause, risk, {}, InMemoryLedger(), cfg)
    asyncio.run(Orchestrator(store, lease, pipeline_runner=runner).run(session))
    assert session.status == SessionStatus.COMPLETED
    assert session.result["schema_version"] == "dev_pipeline_result_v1"
    assert session.result["merged"]["schema_version"] == "risk_merged_v1"
    assert session.result["risk_records"]
    assert clause.requests and risk.requests
    for request in clause.requests + risk.requests:
        payload = json.dumps(request, ensure_ascii=False)
        assert "Nguyễn Văn An" not in payload
        assert "001234567890" not in payload
    assert any(related["relation"] == "REFERS_TO"
               for request in risk.requests for item in request["items"]
               for related in item["related_clauses"])
    assert any(record["related_clause_ids"] for record in session.result["risk_records"])


def test_injected_runner_observes_cancel_callback():
    store, lease = InMemorySessionStore(), ProcessingLease()
    session = store.create(Role.EMPLOYEE)
    assert lease.try_acquire(session.session_id) == session.session_id
    clause, risk = FakeProvider("clause"), FakeProvider("risk")
    cfg = SimpleNamespace(GEMINI_MODEL_ID="fake-model", CLAUSE_BATCH_SIZE=20,
                          RISK_BATCH_SIZE=6, LLM_PARALLELISM=1,
                          LLM_TIMEOUT_SECONDS=5, LLM_AUTO_RETRY=0,
                          CLAUSE_GRAPH_MAX_RELATED=3, CLAUSE_GRAPH_MAX_CONTEXT_CHARS=6000)
    runner = make_pipeline_runner(SOURCE, clause, risk, {}, InMemoryLedger(), cfg)
    session.cancelled = True
    asyncio.run(Orchestrator(store, lease, pipeline_runner=runner).run(session))
    assert not clause.requests and not risk.requests
    assert session.status != SessionStatus.COMPLETED


def _corpus(*, effective_to=None):
    provision = LegalProvision("BLLD2019:art17", "BLLD2019", "Bộ luật Lao động",
                               "2019", "17", None, None, ("BLLD2019", "art17"),
                               "Điều cấm về giữ giấy tờ.",
                               date(2021, 1, 1), effective_to)
    return LegalCorpus("v1", "v1", "Asia/Ho_Chi_Minh", "APPROVED", (provision,), (),
                       {"COMPENSATION_BENEFITS": {"BLLD2019:art17": 1.0}})


def _run_with_citation(citation_id, *, corpus=None):
    store, lease = InMemorySessionStore(), ProcessingLease()
    session = store.create(Role.EMPLOYEE)
    assert lease.try_acquire(session.session_id) == session.session_id
    clause, risk = FakeProvider("clause"), FakeProvider("risk", citation_id)
    cfg = SimpleNamespace(GEMINI_MODEL_ID="fake-model", CLAUSE_BATCH_SIZE=20,
                          RISK_BATCH_SIZE=6, LLM_PARALLELISM=1,
                          LLM_TIMEOUT_SECONDS=5, LLM_AUTO_RETRY=0,
                          CLAUSE_GRAPH_MAX_RELATED=3, CLAUSE_GRAPH_MAX_CONTEXT_CHARS=6000)
    candidates = {"BLLD2019:art17": LegalCandidate("BLLD2019:art17",
                                                    "Điều cấm về giữ giấy tờ.")}
    runner = make_pipeline_runner(SOURCE, clause, risk, candidates, InMemoryLedger(), cfg,
                                  corpus=corpus or _corpus(),
                                  candidate_ids_by_clause={f"cl_{i:04d}": ["BLLD2019:art17"]
                                                           for i in range(1, 7)})
    asyncio.run(Orchestrator(store, lease, pipeline_runner=runner).run(session))
    assert session.status == SessionStatus.COMPLETED
    return session.result


def test_valid_citation_is_assembled_with_code_severity_and_canonical_quote():
    result = _run_with_citation("BLLD2019:art17")
    assert result["merged"]["citations"]
    for record in result["risk_records"]:
        assert record["severity"] == "HIGH"  # taxonomy table, never FakeProvider
        assert record["citation_ids"] == ["BLLD2019:art17"]
        assert SOURCE[record["start_char"]:record["end_char"]] == record["quote"]


def test_outside_candidate_citation_is_dropped_and_severity_cleared():
    result = _run_with_citation("OUTSIDE_CANDIDATE")
    assert result["merged"]["citations"] == []
    for record in result["risk_records"]:
        assert record["citation_ids"] == []
        assert record["evidence_status"] == "INSUFFICIENT_EVIDENCE"
        assert record["severity"] is None
        assert "Điều 99" not in record["explanation"]


def test_expired_citation_is_dropped_and_severity_cleared():
    result = _run_with_citation("BLLD2019:art17",
                                corpus=_corpus(effective_to=date(2022, 12, 31)))
    assert result["merged"]["citations"] == []
    for record in result["risk_records"]:
        assert record["citation_ids"] == []
        assert record["evidence_status"] == "INSUFFICIENT_EVIDENCE"
        assert record["severity"] is None


def test_approved_corpus_retrieval_populates_risk_candidates():
    store, lease = InMemorySessionStore(), ProcessingLease()
    session = store.create(Role.EMPLOYEE)
    assert lease.try_acquire(session.session_id) == session.session_id
    clause, risk = FakeProvider("clause"), FakeProvider("risk", "BLLD2019:art17")
    cfg = SimpleNamespace(GEMINI_MODEL_ID="fake-model", CLAUSE_BATCH_SIZE=20,
                          RISK_BATCH_SIZE=6, LLM_PARALLELISM=1,
                          LLM_TIMEOUT_SECONDS=5, LLM_AUTO_RETRY=0,
                          CLAUSE_GRAPH_MAX_RELATED=3, CLAUSE_GRAPH_MAX_CONTEXT_CHARS=6000)
    corpus = _corpus()
    retriever = BaselineRetriever(corpus, final_k=1, seed_k=1)
    runner = make_pipeline_runner(SOURCE, clause, risk, {}, InMemoryLedger(), cfg,
                                  corpus=corpus, retriever=retriever)
    asyncio.run(Orchestrator(store, lease, pipeline_runner=runner).run(session))
    assert session.status == SessionStatus.COMPLETED
    assert session.result["merged"]["citations"]
    assert all("BLLD2019:art17" in item["candidate_ids"]
               for request in risk.requests for item in request["items"])
