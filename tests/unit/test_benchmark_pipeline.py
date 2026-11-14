"""X-05 (b): benchmark end-to-end trên input tổng hợp với provider giả + latency injection."""

from app.ai.dev_fake_client import DevFakeClient
from app.ai.provider import InMemoryLedger
from app.ops.benchmark_pipeline import BenchInput, LatencyProvider, benchmark_pipeline
from app.pipeline import PipelineDeps

from tests.integration.test_pipeline_e2e import cfg, docx_bytes


def test_report_has_all_stages_calls_and_no_content():
    provider = LatencyProvider(DevFakeClient(app_env="dev"), 0.01)

    def deps():
        return PipelineDeps(cfg(), provider, InMemoryLedger(), None, None, None, "bench")

    report = benchmark_pipeline([BenchInput("SYN1", docx_bytes(), "x.docx", "synthetic")], deps, repeats=2)
    stages = set(report["stages"])
    assert {"total", "EXTRACTION", "CLAUSE_CLASSIFICATION", "RISK_ANALYSIS", "ASSEMBLY"} <= stages
    assert report["stages"]["CLAUSE_CLASSIFICATION"]["p50_ms"] >= 10  # latency injected
    case = report["cases"][0]
    # 1 lô LLM #1 + 1 lô LLM #2: phần mở đầu trước Điều 1 không đủ điều kiện phân loại (eligibility)
    assert case["calls"] == 2 and {c["role"] for c in report["cases"]} == {"EMPLOYEE", "EMPLOYER"}
    assert report["reserve_suggestion"] == 40
    assert "Nguyễn" not in str(report) and "lương" not in str(report)
