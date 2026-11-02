"""Development sample runner only; never used in demo/eval."""
import json
from pathlib import Path

from app.session.store import Session

_FIXTURE = Path(__file__).resolve().parents[3] / "tests/fixtures/mock_final_result_v1.json"


def sample_result(session: Session) -> dict:
    with _FIXTURE.open(encoding="utf-8") as fixture:
        result = json.load(fixture)
    result["session_id"] = str(session.session_id)
    result["role"] = session.role.value
    result["analysis_date"] = session.analysis_date
    if session.mock_variant == "norisk":
        ordinary_clause = result["clauses"][1]
        ordinary_clause["clause_id"] = "cl_0001"
        ordinary_clause["start_char"] = 0
        ordinary_clause["end_char"] = len(ordinary_clause["original_text"])
        result["canonical_text"] = ordinary_clause["original_text"]
        result["clauses"] = [ordinary_clause]
        result["risks"] = []
        result["citations"] = []
    elif session.mock_variant == "insufficient":
        risk = result["risks"][0]
        risk["evidence_status"] = "INSUFFICIENT_EVIDENCE"
        risk["severity"] = None
        risk["citation_ids"] = []
        risk["explanation"] = "Chưa đủ căn cứ pháp lý trong kho luật đóng để kết luận về điều khoản này."
        result["citations"] = []
    return result
