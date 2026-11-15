"""X-19: `pipeline.analyze()` end-to-end với provider giả tất định + corpus thật trong repo.

Phủ: final_result_v1 hợp schema; INV-02/03 (partition, substring); INV-04 (payload ra provider chỉ có masked
text, không offset/canonical PII); INV-06/07 (citation ⊂ candidate, INSUFFICIENT ⇒ severity null); stop_after;
REJECTED; cancel; trace context không chứa text.
"""

import asyncio
import io
import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.ai.dev_fake_client import DevFakeClient
from app.ai.provider import InMemoryLedger
from app.core.enums import Stage
from app.domain.errors import AiTimeout, StageCancelled, ValidationReject
from app.legal.baseline_retriever import BaselineRetriever
from app.legal.corpus_loader import load_corpus
from app.legal.data_graph import DataGraph
from app.pipeline import PipelineArtifacts, PipelineDeps, analyze, resume_state
from docx import Document
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "ai_pipeline/schemas/final_result_v1.json").read_text(encoding="utf-8"))

CONTRACT_LINES = [
    "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
    "HỢP ĐỒNG LAO ĐỘNG",
    "Người sử dụng lao động: Công ty TNHH Minh Phát. Người lao động: Nguyễn Văn An, điện thoại 0912345678.",
    "Điều 1. Công việc",
    "Người lao động làm chuyên viên kế toán, chức danh chuyên viên, tại trụ sở công ty.",
    "Điều 2. Thời gian thử việc",
    "1. Thời gian thử việc là 60 ngày kể từ ngày ký.",
    "2. Lương thử việc bằng 85% mức lương tại Điều 3.",
    "Điều 3. Tiền lương",
    "Mức lương chính 10.000.000 đồng/tháng, trả vào ngày 5 hằng tháng.",
    "Điều 4. Giấy tờ",
    "Công ty giữ bản chính văn bằng của người lao động trong suốt thời hạn hợp đồng.",
]


def docx_bytes(lines=CONTRACT_LINES) -> bytes:
    doc = Document()
    for line in lines:
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def cfg(**kw):
    base = dict(GEMINI_MODEL_ID="dev-fake-provider", CLAUSE_BATCH_SIZE=20, RISK_BATCH_SIZE=6, LLM_PARALLELISM=2,
                LLM_TIMEOUT_SECONDS=5, LLM_AUTO_RETRY=1, MAX_PDF_PAGES=30, MAX_DOCX_CHARS=100000, MAX_UPLOAD_MB=10,
                MAX_CLAUSES=150, SCOPE_TITLE_SCAN_CHARS=1000, CLAUSE_GRAPH_ENABLED=True, DATA_GRAPH_ENABLED=True,
                RETRIEVAL_SEED_K=3, RETRIEVAL_FINAL_K=8, GRAPH_MAX_NEIGHBORS_PER_SEED=4, GRAPH_MAX_CHILDREN_PER_SEED=2,
                CLAUSE_GRAPH_MAX_RELATED=3, CLAUSE_GRAPH_MAX_CONTEXT_CHARS=6000, TEMPERATURE=0.0)
    base.update(kw)
    return SimpleNamespace(**base)


class Capturing:
    """Bọc provider, ghi lại mọi payload gửi đi (INV-04 outbound capture)."""

    def __init__(self, inner, fail_on=None):
        self.inner, self.sent, self.fail_on = inner, [], fail_on

    async def generate_structured(self, *, model_id, messages, response_schema, timeout_s):
        self.sent.append(json.loads(messages[1]["content"]))
        kind = self.sent[-1].get("schema_version", "")
        if self.fail_on and kind.startswith(self.fail_on):
            raise AiTimeout()
        return await self.inner.generate_structured(model_id=model_id, messages=messages,
                                                    response_schema=response_schema, timeout_s=timeout_s)


@pytest.fixture(scope="module")
def legal():
    corpus = load_corpus(ROOT / "data/legal_corpus", allow_draft=True)
    return corpus, BaselineRetriever(corpus, final_k=8, seed_k=3, allow_draft=True), DataGraph(corpus, allow_draft=True)


def make_deps(legal, provider=None, **kw):
    corpus, retriever, graph = legal
    return PipelineDeps(cfg(**kw), provider or Capturing(DevFakeClient(app_env="dev")), InMemoryLedger(),
                        corpus, retriever, graph, "test-commit")


def run(coro):
    return asyncio.run(coro)


def test_end_to_end_final_result_is_schema_valid(legal):
    deps = make_deps(legal)
    stages = []
    art = run(analyze(docx_bytes(), "hd.docx", "EMPLOYEE", session_id="5f0c8c1e-2f6a-4a7e-9b1d-0c6f4f6b8a11",
                      analysis_date=date(2026, 11, 13), deps=deps, on_stage=stages.append))
    result = art.final_result
    errors = sorted(Draft202012Validator(SCHEMA).iter_errors(result), key=lambda e: e.path)
    assert not errors, errors[0].message
    assert stages == [Stage.EXTRACTION, Stage.SCOPE_PRECHECK, Stage.PII_MASKING, Stage.SEGMENTATION,
                      Stage.CLAUSE_GRAPH, Stage.CLAUSE_CLASSIFICATION, Stage.LEGAL_RETRIEVAL, Stage.RISK_ANALYSIS,
                      Stage.CITATION_VALIDATION, Stage.ASSEMBLY]
    text = result["canonical_text"]
    pos = 0
    for c in result["clauses"]:                                    # INV-02/03
        assert text[c["start_char"]:c["end_char"]] == c["original_text"]
        assert c["start_char"] >= pos
        pos = c["end_char"]
    clause_ids = {c["clause_id"] for c in result["clauses"]}
    cited = {c["citation_id"] for c in result["citations"]}
    risky = {r["clause_id"]: r for r in result["risks"]}
    assert risky, "fake provider phải báo ít nhất rủi ro giữ bản chính văn bằng"
    for r in result["risks"]:
        assert r["clause_id"] in clause_ids
        assert set(r["citation_ids"]) <= cited                      # INV-06
        assert set(r["citation_ids"]) <= set(art.candidates[r["clause_id"]])
        if r["evidence_status"] == "INSUFFICIENT_EVIDENCE":          # INV-07
            assert r["severity"] is None and r["citation_ids"] == []
    assert result["version_pins"]["app_commit"] == "test-commit"
    assert result["version_pins"]["extraction_version"] == "extract_docx_v2"


def test_outbound_payload_is_masked_without_offsets(legal):
    deps = make_deps(legal)
    run(analyze(docx_bytes(), "hd.docx", "EMPLOYER", session_id="s", analysis_date=date(2026, 11, 13), deps=deps))
    dumped = json.dumps(deps.provider.sent, ensure_ascii=False)
    assert "0912345678" not in dumped and "Nguyễn Văn An" not in dumped          # PII đã che
    for key in ("start_char", "end_char", "canonical_text", "original_text", "structure"):
        assert f'"{key}"' not in dumped
    kinds = [p["schema_version"] for p in deps.provider.sent]
    assert kinds[0].startswith("clause_") and kinds[-1].startswith("risk_analysis_request")
    assert all("role" not in p for p in deps.provider.sent if p["schema_version"].startswith("clause_"))


def test_context_trace_has_ids_only(legal):
    deps = make_deps(legal)
    art = run(analyze(docx_bytes(), "hd.docx", "EMPLOYEE", session_id="s", analysis_date=date(2026, 11, 13),
                      deps=deps))
    blob = json.dumps(art.traces, ensure_ascii=False)
    assert "lương" not in blob.lower() and any(t["related"] for t in art.traces)
    assert any(r["relation"] == "REFERS_TO" for t in art.traces for r in t["related"])  # "tại Điều 3"


def test_stop_after_segmentation_makes_no_llm_call(legal):
    deps = make_deps(legal)
    art = run(analyze(docx_bytes(), "hd.docx", "EMPLOYEE", session_id="s", analysis_date=date(2026, 11, 13),
                      deps=deps, stop_after=Stage.SEGMENTATION))
    assert art.segmentation is not None and art.final_result is None and deps.provider.sent == []


def test_not_labor_contract_rejected(legal):
    data = docx_bytes(["HỢP ĐỒNG MUA BÁN", "Bên bán giao hàng cho bên mua theo đơn đặt hàng số 12. " * 4])
    with pytest.raises(ValidationReject) as exc:
        run(analyze(data, "x.docx", "EMPLOYEE", session_id="s", analysis_date=date(2026, 11, 13),
                    deps=make_deps(legal)))
    assert exc.value.code == "NOT_LABOR_CONTRACT"


def test_wrong_extension_rejected(legal):
    with pytest.raises(ValidationReject):
        run(analyze(docx_bytes(), "x.pdf", "EMPLOYEE", session_id="s", analysis_date=date(2026, 11, 13),
                    deps=make_deps(legal)))


def test_cancel_between_stages(legal):
    calls = {"n": 0}

    def cancel():
        calls["n"] += 1
        return calls["n"] > 3
    with pytest.raises(StageCancelled):
        run(analyze(docx_bytes(), "hd.docx", "EMPLOYEE", session_id="s", analysis_date=date(2026, 11, 13),
                    deps=make_deps(legal), check_cancel=cancel))


def test_ai_failure_keeps_local_artifacts_for_resume(legal):
    failing = Capturing(DevFakeClient(app_env="dev"), fail_on="risk_analysis")
    deps = make_deps(legal, provider=failing)
    art = PipelineArtifacts()
    with pytest.raises(AiTimeout):
        run(analyze(docx_bytes(), "hd.docx", "EMPLOYEE", session_id="s", analysis_date=date(2026, 11, 13),
                    deps=deps, into=art))
    state = resume_state(art, deps)
    assert state is not None and state.matches(deps)
    ok = make_deps(legal)
    resumed = run(analyze(docx_bytes(), "hd.docx", "EMPLOYEE", session_id="s", analysis_date=date(2026, 11, 13),
                          deps=ok, resume=state))
    assert resumed.final_result is not None
    assert ok.provider.sent[0]["schema_version"].startswith("clause_")  # chạy lại từ LLM #1, không extraction


def test_graph_off_has_no_context_but_same_spans(legal):
    on = run(analyze(docx_bytes(), "hd.docx", "EMPLOYEE", session_id="s", analysis_date=date(2026, 11, 13),
                     deps=make_deps(legal)))
    off = run(analyze(docx_bytes(), "hd.docx", "EMPLOYEE", session_id="s", analysis_date=date(2026, 11, 13),
                      deps=make_deps(legal, CLAUSE_GRAPH_ENABLED=False)))
    assert on.final_result["clauses"] == off.final_result["clauses"]
    assert all(not t["related"] for t in off.traces)
