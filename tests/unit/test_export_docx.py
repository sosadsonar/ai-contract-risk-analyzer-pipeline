"""C-21 (b): export DOCX qua ReportModel — đủ quote, mức độ / chưa đủ căn cứ / cần xem xét, liên quan, căn cứ
(nguyên văn Khoản), disclaimer + data notice; không rủi ro ⇒ câu cố định, không chữ "an toàn"."""

import copy
import io
import json
from pathlib import Path

from app.result.export_docx import export_docx
from app.result.report_model import INSUFFICIENT_MESSAGE, NEEDS_REVIEW_MESSAGE, NO_RISK_MESSAGE, build_report_model
from docx import Document

FIXTURE = Path(__file__).resolve().parents[2] / "backend/app/session/fixtures/mock_final_result_v1.json"


def _text(data: bytes) -> str:
    return "\n".join(p.text for p in Document(io.BytesIO(data)).paragraphs)


def _fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_export_contains_required_sections():
    result = _fixture()
    result["citations"][0]["clause"] = "1"
    text = _text(export_docx(build_report_model(result)))
    assert result["disclaimer"] in text and result["data_notice"] in text
    assert "Điều 1" in text and "Mức độ: Cao" in text
    assert result["clauses"][0]["original_text"].strip() in text
    assert "Căn cứ: Khoản 1 Điều 17" in text and result["citations"][0]["content"] in text
    assert "Tóm tắt" in text and "cl_0001" not in text


def test_insufficient_needs_review_and_related():
    result = _fixture()
    risk = result["risks"][0]
    insufficient = dict(risk, evidence_status="INSUFFICIENT_EVIDENCE", severity=None, citation_ids=[])
    review = dict(copy.deepcopy(risk), clause_id="cl_0002", evidence_status="INSUFFICIENT_EVIDENCE", severity=None,
                  citation_ids=[], needs_review=True, related_clause_ids=["cl_0001"])
    result["risks"] = [insufficient, review]
    model = build_report_model(result)
    assert model.summary.insufficient == 1 and model.summary.needs_review == 1
    text = _text(export_docx(model))
    assert INSUFFICIENT_MESSAGE in text and NEEDS_REVIEW_MESSAGE in text
    assert "Liên quan: Điều 1" in text
    assert text.count("Mức độ:") == 1  # bản ghi cần xem xét không có mức độ


def test_no_risk_message_without_safe_wording():
    result = _fixture()
    result["risks"], result["citations"] = [], []
    text = _text(export_docx(build_report_model(result)))
    assert NO_RISK_MESSAGE in text and "an toàn" not in text
