"""The configured route runs the real pipeline path with fake providers."""

import json
import subprocess
import time
from pathlib import Path

from app.ai.provider import InMemoryLedger, LLMResponse
from app.domain.errors import ValidationReject
from app.main import app
from app.session.pipeline_runner import make_pipeline_runner
from fastapi.testclient import TestClient

SOURCE = (
    "HỢP ĐỒNG LAO ĐỘNG\n"
    "Điều 1. Quy định chung:\n"
    "1.1 Người lao động Ông Nguyễn Văn An, CCCD: 001234567890 thực hiện công việc.\n"
    "Điều 2. Tiền lương:\n"
    "2.1 Tiền lương được áp dụng theo Điều 1 của Hợp đồng này."
)
BASE = "/api/v1/sessions"


class FakeProvider:
    def __init__(self, kind):
        self.kind = kind

    async def generate_structured(self, *, model_id, messages, response_schema, timeout_s):
        request = json.loads(messages[1]["content"])
        if self.kind == "clause":
            data = {"items": [{"clause_id": item["clause_id"],
                               "clause_labels": ["JOB_INFO"]}
                              for item in request["items"]]}
        else:
            data = {"schema_version": "risk_output_v2", "items": [
                {"clause_id": item["clause_id"], "basis_type": "AMBIGUOUS",
                 "risk_labels": ["UNILATERAL_CHANGE"], "citation_ids": [],
                 "evidence_status": "INSUFFICIENT_EVIDENCE",
                 "explanation": "Nội dung công việc chưa xác định đủ rõ."}
                for item in request["items"]]}
        return LLMResponse(data, model_id)


def _wait_status(client, sid, target):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        state = client.get(f"{BASE}/{sid}/status").json()
        if state["status"] in target:
            return state
        time.sleep(0.01)
    raise AssertionError("session did not reach a terminal state")


def test_route_injected_runner_writes_final_result_with_real_head(monkeypatch):
    monkeypatch.delenv("APP_COMMIT", raising=False)
    clause, risk = FakeProvider("clause"), FakeProvider("risk")
    with TestClient(app) as client:
        monkeypatch.setattr(app.state.settings, "GEMINI_MODEL_ID", "fake-model")
        transitions = []
        original_transition = app.state.orchestrator.transition

        def record_transition(session, status, stage, error_code=None, result=None):
            transitions.append(status.value)
            return original_transition(session, status, stage, error_code, result)

        monkeypatch.setattr(app.state.orchestrator, "transition", record_transition)
        async def factory(upload, session):
            assert upload.file_content == b"%PDF-1.4\n%%EOF\n"
            return make_pipeline_runner(SOURCE, clause, risk, {}, InMemoryLedger(),
                                        app.state.settings)

        app.state.pipeline_runner_factory = factory
        try:
            response = client.post(BASE, data={"role": "EMPLOYEE"},
                                   files={"file": ("sample.pdf", b"%PDF-1.4\n%%EOF\n")})
            assert response.status_code == 201
            sid = response.json()["session_id"]
            seen = {"UPLOADED"}
            state = _wait_status(client, sid, {"COMPLETED", "FAILED"})
            seen.add(state["status"])
            assert state["status"] == "COMPLETED", state
            result = client.get(f"{BASE}/{sid}/result").json()
            assert result["schema_version"] == "final_result_v1"
            assert result["canonical_text"] == SOURCE
            repo = Path(__file__).resolve().parents[2]
            head = subprocess.check_output(
                ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
            assert result["version_pins"]["app_commit"] == head
            assert result["risks"]
            assert {"UPLOADED", "COMPLETED"} <= seen
            assert transitions == ["VALIDATING", "PROCESSING", "COMPLETED"]
        finally:
            del app.state.pipeline_runner_factory


def test_product_factory_rejection_does_not_fall_back_to_sample():
    with TestClient(app) as client:
        async def factory(upload, session):
            raise ValidationReject("NO_EXTRACTABLE_TEXT")

        app.state.pipeline_runner_factory = factory
        try:
            response = client.post(BASE, data={"role": "EMPLOYEE"},
                                   files={"file": ("sample.pdf", b"%PDF-1.4\n%%EOF\n")})
            assert response.status_code == 201
            sid = response.json()["session_id"]
            state = _wait_status(client, sid, {"REJECTED", "COMPLETED", "FAILED"})
            assert state["status"] == "REJECTED"
            assert state["error_code"] == "NO_EXTRACTABLE_TEXT"
            assert client.get(f"{BASE}/{sid}/result").status_code == 409
        finally:
            del app.state.pipeline_runner_factory
