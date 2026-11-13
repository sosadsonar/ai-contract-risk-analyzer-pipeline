"""Build the client result only after masked provider calls have completed."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from app.clause.segmenter import OFFSET_UNIT
from app.risk.taxonomy import severity_for_labels

_PIN_KEYS = frozenset({
    "extraction_version", "clause_taxonomy_version", "risk_taxonomy_version",
    "severity_rubric_version", "corpus_version", "data_graph_version",
    "clause_prompt_version", "risk_prompt_version", "model_id",
    "temperature", "app_commit",
})
_CLAUSE_KEYS = ("clause_id", "start_char", "end_char", "original_text", "clause_labels")
_RISK_KEYS = ("clause_id", "risk_labels", "risk_basis", "severity", "explanation",
              "evidence_status", "citation_ids")
_DISCLAIMER = "Kết quả chỉ hỗ trợ tham khảo rủi ro theo phạm vi phân tích, không thay thế tư vấn pháp lý."
_DATA_NOTICE = "Nội dung hợp đồng được xử lý trong phiên tạm thời và có thể chứa thông tin cá nhân."


def build_final_result_v1(
    *, session_id: str, role: str, analysis_date: str, canonical_text: str,
    clauses: Sequence[Mapping[str, Any]], merged: Mapping[str, Any],
    related_clause_ids: Mapping[str, Sequence[str]],
    version_pins: Mapping[str, Any],
) -> dict[str, Any]:
    """Assemble product fields from canonical spans and backend-validated risks.

    The canonical source enters here, after both providers have returned. This
    function never builds or sends provider requests.
    """
    if not isinstance(canonical_text, str):
        raise ValueError("canonical_text must be text")
    if not all(isinstance(value, str) and value for value in
               (session_id, role, analysis_date)):
        raise ValueError("session identity is incomplete")
    if set(version_pins) != _PIN_KEYS:
        raise ValueError("version pins must contain the 11 required fields")
    if any(not isinstance(version_pins[key], str) or not version_pins[key]
           for key in _PIN_KEYS - {"temperature"}):
        raise ValueError("version pins must be non-empty")
    temperature = version_pins["temperature"]
    if isinstance(temperature, bool) or not isinstance(temperature, (int, float)):
        raise ValueError("version temperature must be numeric")

    result_clauses = []
    clause_by_id = {}
    for source_clause in clauses:
        clause = {key: source_clause[key] for key in _CLAUSE_KEYS}
        start, end = clause["start_char"], clause["end_char"]
        if (not isinstance(start, int) or isinstance(start, bool)
                or not isinstance(end, int) or isinstance(end, bool)
                or not 0 <= start < end <= len(canonical_text)
                or canonical_text[start:end] != clause["original_text"]):
            raise ValueError("clause offset does not match canonical source")
        cid = clause["clause_id"]
        if cid in clause_by_id:
            raise ValueError("duplicate clause ID")
        clause_by_id[cid] = clause
        result_clauses.append(clause)

    citations = list(merged["citations"])
    known_citations = {citation["citation_id"] for citation in citations}
    if len(known_citations) != len(citations):
        raise ValueError("duplicate citation ID")
    risks = []
    for source_risk in merged["clauses"]:
        risk = {key: source_risk[key] for key in _RISK_KEYS}
        cid = risk["clause_id"]
        clause = clause_by_id.get(cid)
        if clause is None:
            raise ValueError("risk refers to an unknown clause")
        if (source_risk["start_char"] != clause["start_char"]
                or source_risk["end_char"] != clause["end_char"]
                or source_risk["original_text"] != clause["original_text"]):
            raise ValueError("risk offset does not match canonical clause")
        if [item["label"] for item in risk["risk_basis"]] != risk["risk_labels"]:
            raise ValueError("risk basis must match risk labels")
        basis_types = {item["basis_type"] for item in risk["risk_basis"]}
        if len(basis_types) != 1:
            raise ValueError("risk basis types are inconsistent")
        expected = (severity_for_labels(risk["risk_labels"], next(iter(basis_types)), role)
                    if risk["evidence_status"] == "SUPPORTED" else None)
        if risk["severity"] != (expected.value if expected else None):
            raise ValueError("risk severity differs from taxonomy")
        if not set(risk["citation_ids"]) <= known_citations:
            raise ValueError("risk cites an unresolved provision")
        risk["quote"] = clause["original_text"]
        risk["start_char"] = clause["start_char"]
        risk["end_char"] = clause["end_char"]
        related = list(related_clause_ids.get(cid, ()))
        if any(item not in clause_by_id for item in related):
            raise ValueError("related clause ID is unknown")
        if related:
            risk["related_clause_ids"] = related
        risks.append(risk)

    return {
        "schema_version": "final_result_v1", "offset_unit": OFFSET_UNIT,
        "session_id": session_id, "role": role, "status": "COMPLETED",
        "analysis_date": analysis_date, "canonical_text": canonical_text,
        "clauses": result_clauses, "risks": risks, "citations": citations,
        "disclaimer": _DISCLAIMER, "data_notice": _DATA_NOTICE,
        "version_pins": dict(version_pins),
    }
