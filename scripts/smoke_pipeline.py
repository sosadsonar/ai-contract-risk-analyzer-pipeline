"""Smoke toàn pipeline (X-19) không cần API key: DOCX tổng hợp → analyze() với DevFakeClient → final_result_v1.

Chạy: `python scripts/smoke_pipeline.py` từ thư mục gốc. Thay cho `ai_pipeline/test_pipeline.py` (legacy, đã xóa).
In ra số liệu tóm tắt (không in nội dung hợp đồng). Thoát mã 1 nếu kết quả không hợp schema.
"""

import asyncio
import io
import json
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT)]

from app.ai.dev_fake_client import FAKE_MODEL_ID, DevFakeClient  # noqa: E402
from app.ai.provider import InMemoryLedger  # noqa: E402
from app.legal.baseline_retriever import BaselineRetriever  # noqa: E402
from app.legal.corpus_loader import load_corpus  # noqa: E402
from app.legal.data_graph import DataGraph  # noqa: E402
from app.pipeline import PipelineDeps, analyze  # noqa: E402
from docx import Document  # noqa: E402

LINES = [
    "HỢP ĐỒNG LAO ĐỘNG",
    "Người sử dụng lao động: Công ty A. Người lao động: Trần Thị B, điện thoại 0987654321.",
    "Điều 1. Công việc", "Người lao động làm nhân viên kinh doanh tại chi nhánh.",
    "Điều 2. Thời gian thử việc", "Thời gian thử việc là 60 ngày.",
    "Điều 3. Giấy tờ", "Công ty giữ bản chính văn bằng của người lao động.",
]


def main() -> int:
    doc = Document()
    for line in LINES:
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    cfg = SimpleNamespace(GEMINI_MODEL_ID=FAKE_MODEL_ID, CLAUSE_BATCH_SIZE=20, RISK_BATCH_SIZE=6, LLM_PARALLELISM=2,
                          LLM_TIMEOUT_SECONDS=5, LLM_AUTO_RETRY=1, MAX_PDF_PAGES=30, MAX_DOCX_CHARS=100000,
                          MAX_UPLOAD_MB=10, MAX_CLAUSES=150, SCOPE_TITLE_SCAN_CHARS=1000, CLAUSE_GRAPH_ENABLED=True,
                          DATA_GRAPH_ENABLED=True, RETRIEVAL_SEED_K=3, RETRIEVAL_FINAL_K=8,
                          GRAPH_MAX_NEIGHBORS_PER_SEED=4, GRAPH_MAX_CHILDREN_PER_SEED=2, CLAUSE_GRAPH_MAX_RELATED=3,
                          CLAUSE_GRAPH_MAX_CONTEXT_CHARS=6000, TEMPERATURE=0.0)
    corpus = load_corpus(ROOT / "data/legal_corpus", allow_draft=True)
    deps = PipelineDeps(cfg, DevFakeClient(app_env="dev"), InMemoryLedger(), corpus,
                        BaselineRetriever(corpus, allow_draft=True), DataGraph(corpus, allow_draft=True), "smoke")
    art = asyncio.run(analyze(buf.getvalue(), "smoke.docx", "EMPLOYEE", session_id="smoke",
                              analysis_date=date.today(), deps=deps))
    result = art.final_result
    try:
        from jsonschema import Draft202012Validator
        schema = json.loads((ROOT / "ai_pipeline/schemas/final_result_v1.json").read_text(encoding="utf-8"))
        errors = list(Draft202012Validator(schema).iter_errors(result))
    except ImportError:
        errors = []
    print(f"clauses={len(result['clauses'])} risks={len(result['risks'])} citations={len(result['citations'])} "
          f"llm_calls={deps.ledger.calls} schema_errors={len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
