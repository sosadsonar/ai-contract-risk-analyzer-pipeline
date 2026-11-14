"""Consumer-visible dev sample lifecycle and retention."""
import asyncio
import io
import threading
import time
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from app.core.enums import SessionStatus, Stage
from app.main import app
from app.session.store import utcnow
from docx import Document
from fastapi.testclient import TestClient

BASE = "/api/v1/sessions"
PDF = b"%PDF-1.4\n%%EOF\n"


@pytest.fixture
def client(sample_mode):
    with TestClient(app) as api:
        assert not api.app.state.pipeline_enabled
        yield api


def create(client, role="EMPLOYEE", name="sample.pdf", data=PDF):
    response = client.post(BASE, data={"role": role}, files={"file": (name, data)})
    assert response.status_code == 201, response.text
    return response.json()["session_id"]


def completed(client, sid):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        state = client.get(f"{BASE}/{sid}/status").json()
        if state["status"] == "COMPLETED":
            return state
        time.sleep(0.02)
    pytest.fail("Sample transition did not complete")


def test_result_export_delete_and_tombstone(client, monkeypatch):
    release = threading.Event()
    original_run = app.state.orchestrator.run

    async def gated_run(session, error_code=None):
        await asyncio.to_thread(release.wait, 10)
        await original_run(session, error_code)

    monkeypatch.setattr(app.state.orchestrator, "run", gated_run)
    try:
        sid = create(client)
        path = f"{BASE}/{sid}"
        assert client.get(path + "/status").json()["updated_at"].endswith("Z")
        assert client.get(path + "/result").json()["error"]["code"] == "SESSION_NOT_READY"
        assert client.post(path + "/retry").json()["error"]["code"] == "INVALID_SESSION_STATE"
    finally:
        release.set()
    completed(client, sid)
    result = client.get(path + "/result").json()
    assert result["session_id"] == sid
    assert result["role"] == "EMPLOYEE"
    assert result["schema_version"] == "final_result_v1"
    for clause in result["clauses"]:
        assert result["canonical_text"][clause["start_char"]:clause["end_char"]] == clause["original_text"]
    exported = client.get(path + "/export?format=docx")
    assert exported.status_code == 200 and exported.content.startswith(b"PK")
    paragraphs = "\n".join(p.text for p in Document(io.BytesIO(exported.content)).paragraphs)
    assert result["risks"][0]["explanation"] in paragraphs
    assert client.get(path + "/export?format=pdf").status_code == 501
    assert client.delete(path).json()["status"] == "EXPIRED"
    assert client.delete(path).json()["status"] == "EXPIRED"
    expired = client.get(path + "/status").json()
    assert expired["status"] == "EXPIRED" and expired["updated_at"].endswith("Z")
    assert client.get(path + "/result").status_code == 410
    assert client.get(f"{BASE}/{uuid4()}/status").status_code == 404


@pytest.mark.parametrize("name", ["emoji.pdf", "insufficient.pdf", "norisk.pdf"])
def test_dev_result_variants_respect_highlight_and_evidence_contract(client, name):
    sid = create(client, name=name)
    completed(client, sid)
    result = client.get(f"{BASE}/{sid}/result").json()
    text = result["canonical_text"]
    assert "📄" in text
    assert result["offset_unit"] == "unicode_code_point"
    cursor = 0
    for clause in result["clauses"]:
        assert clause["start_char"] == cursor
        cursor = clause["end_char"]
        assert text[clause["start_char"]:cursor] == clause["original_text"]
    assert cursor == len(text)
    if name == "insufficient.pdf":
        risk = result["risks"][0]
        assert risk["evidence_status"] == "INSUFFICIENT_EVIDENCE"
        assert risk["severity"] is None and risk["citation_ids"] == []
        assert len(risk["risk_basis"]) == len(risk["risk_labels"])
    elif name == "norisk.pdf":
        assert result["risks"] == [] and result["citations"] == []
        assert "giữ bản chính" not in text
    else:
        assert result["risks"][0]["evidence_status"] == "SUPPORTED"
    client.delete(f"{BASE}/{sid}")


def test_retry_limit_and_lazy_expiry(client):
    sid = create(client)
    session = app.state.store.get(UUID(sid))
    session.task.cancel()
    app.state.lease.release(session.session_id)
    orchestrator = app.state.orchestrator
    if session.status == SessionStatus.UPLOADED:
        orchestrator.transition(session, SessionStatus.VALIDATING, Stage.EXTRACTION)
    orchestrator.transition(session, SessionStatus.FAILED, Stage.EXTRACTION, "INTERNAL_ERROR")
    path = f"{BASE}/{sid}"
    for count in (1, 2):
        response = client.post(path + "/retry")
        assert response.status_code == 200, response.text
        body = response.json()
        assert set(body) == {
            "session_id", "status", "stage", "progress",
            "manual_retry_count", "error_code", "updated_at",
        }
        assert body["status"] == "VALIDATING" and body["stage"] == "EXTRACTION"
        assert body["progress"] == {"completed_units": 1, "total_units": 3}
        assert body["error_code"] is None
        assert body["updated_at"].endswith("Z")
        assert body["manual_retry_count"] == count
        session.task.cancel()
        app.state.lease.release(session.session_id)
        orchestrator.transition(session, SessionStatus.FAILED, Stage.EXTRACTION, "INTERNAL_ERROR")
    assert client.post(path + "/retry").json()["error"]["code"] == "RETRY_LIMIT_EXCEEDED"
    session.last_activity_at = utcnow() - timedelta(minutes=61)
    assert client.get(path + "/status").json()["status"] == "EXPIRED"
    app.state.db.prune_tombstones(utcnow() + timedelta(hours=25))
    assert client.get(path + "/status").status_code == 404
