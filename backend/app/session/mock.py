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
    return result
