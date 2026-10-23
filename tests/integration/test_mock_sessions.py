"""Consumer-visible behavior of the disposable dev HTTP contract."""

import io
import time
from datetime import timedelta
from uuid import uuid4

import pytest
from docx import Document
from fastapi.testclient import TestClient

from app.core.enums import SessionStatus
from app.main import app
from app.session.mock import utcnow

BASE = "/api/v1/sessions"
PDF = b"%PDF-1.4\n%%EOF\n"


@pytest.fixture
def client():
    app.state.mock_store.sessions.clear()
    app.state.mock_store.tombstones.clear()
    with TestClient(app) as api:
        yield api
    app.state.mock_store.sessions.clear()
    app.state.mock_store.tombstones.clear()


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
    pytest.fail("Mock transition did not complete without status-dependent progress")


def test_result_export_delete_and_tombstone(client):
    sid = create(client)
    path = f"{BASE}/{sid}"
    assert client.get(path + "/result").json()["error"]["code"] == "SESSION_NOT_READY"
    assert client.post(path + "/retry").json()["error"]["code"] == "INVALID_SESSION_STATE"
    completed(client, sid)
    result = client.get(path + "/result").json()
    assert result["session_id"] == sid
    assert result["role"] == "EMPLOYEE"
    assert result["schema_version"] == "final_result_v1"
    for clause in result["clauses"]:
        assert result["canonical_text"][clause["start_char"]:clause["end_char"]] == clause["original_text"]
    assert len(result["clauses"]) == 2 and len(result["risks"]) == 1
    exported = client.get(path + "/export?format=docx")
    assert exported.status_code == 200 and exported.content.startswith(b"PK")
    paragraphs = "\n".join(p.text for p in Document(io.BytesIO(exported.content)).paragraphs)
    assert result["risks"][0]["explanation"] in paragraphs
    assert result["citations"][0]["citation_id"] in paragraphs
    assert client.get(path + "/export?format=pdf").json()["error"]["code"] == "FEATURE_NOT_ENABLED"
    assert client.delete(path).json()["status"] == "EXPIRED"
    assert client.delete(path).json()["status"] == "EXPIRED"
    assert client.get(path + "/status").json()["status"] == "EXPIRED"
    assert client.get(path + "/result").status_code == 410
    assert client.get(f"{BASE}/{uuid4()}/status").status_code == 404
    assert client.get(f"{BASE}/garbage/status").status_code == 404


def test_retry_limit_and_lazy_expiry(client):
    sid = create(client)
    session = app.state.mock_store.sessions[next(iter(app.state.mock_store.sessions))]
    if session.task:
        session.task.cancel()
    session.status = SessionStatus.FAILED
    session.error_code = "MOCK_FAILURE"
    path = f"{BASE}/{sid}"
    assert client.get(path + "/result").json()["error"]["code"] == "SESSION_NOT_READY"
    for count in (1, 2):
        response = client.post(path + "/retry")
        assert response.status_code == 200, response.text
        assert response.json()["manual_retry_count"] == count
        if session.task:
            session.task.cancel()
        session.status = SessionStatus.FAILED
        session.error_code = "MOCK_FAILURE"
    assert client.post(path + "/retry").json()["error"]["code"] == "RETRY_LIMIT_EXCEEDED"
    session.last_activity_at = utcnow() - timedelta(minutes=61)
    assert client.get(path + "/status").json()["status"] == "EXPIRED"
    app.state.mock_store.tombstones[session.session_id] = utcnow() - timedelta(hours=25)
    assert client.get(path + "/status").status_code == 404
