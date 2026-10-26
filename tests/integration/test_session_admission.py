"""Admission precedence, streaming boundaries and cancellation races."""
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import UUID

from app.core.enums import SessionStatus, Stage
from app.main import app
from app.session.store import utcnow
from fastapi.testclient import TestClient

BASE = "/api/v1/sessions"


def create(client, data=b"%PDF-1.4"):
    return client.post(BASE, data={"role": "EMPLOYEE"}, files={"file": ("x.pdf", data)})


def test_role_gate_and_file_boundaries():
    with TestClient(app) as client:
        assert client.post(BASE, files={"file": ("x.pdf", b"%PDF-")}).json()["error"]["code"] == "ROLE_REQUIRED"
        assert len(app.state.store.sessions) == 0
        response = create(client, b"%PDF-" + b"a" * (10 * 1024 * 1024 - 5))
        assert response.status_code == 201
        sid = response.json()["session_id"]
        time.sleep(.2)
        assert client.get(f"{BASE}/{sid}/status").json()["status"] == "COMPLETED"
        client.delete(f"{BASE}/{sid}")
        response = create(client, b"%PDF-" + b"a" * (10 * 1024 * 1024 - 4))
        assert response.status_code == 201
        sid = response.json()["session_id"]
        time.sleep(.2)
        state = client.get(f"{BASE}/{sid}/status").json()
        assert state["status"] == "REJECTED" and state["error_code"] == "FILE_TOO_LARGE"
        assert client.get(f"{BASE}/{sid}/result").status_code == 409


def test_busy_precedes_session_creation_and_retry_counter():
    with TestClient(app) as client:
        first = create(client).json()["session_id"]
        second = create(client)
        assert second.status_code == 409 and second.json()["error"]["code"] == "SYSTEM_BUSY"
        assert len(app.state.store.sessions) == 1
        session = app.state.store.get(UUID(first))
        session.task.cancel()
        app.state.lease.release(session.session_id)
        if session.status == SessionStatus.UPLOADED:
            app.state.orchestrator.transition(session, SessionStatus.VALIDATING, Stage.EXTRACTION)
        app.state.orchestrator.transition(session, SessionStatus.FAILED, Stage.EXTRACTION, "INTERNAL_ERROR")
        holder = app.state.lease.try_acquire()
        response = client.post(f"{BASE}/{first}/retry")
        assert response.status_code == 409 and session.manual_retry_count == 0
        app.state.lease.release(holder)
        assert client.post(f"{BASE}/{first}/retry").json()["status"] == "VALIDATING"
        client.delete(f"{BASE}/{first}")
        assert not app.state.orchestrator.transition(session, SessionStatus.PROCESSING, Stage.RISK_ANALYSIS)
        assert app.state.store.get(session.session_id) is None


def test_status_does_not_extend_ttl_but_result_does():
    with TestClient(app) as client:
        sid = create(client).json()["session_id"]
        session = app.state.store.get(UUID(sid))
        session.last_activity_at = utcnow() - timedelta(minutes=59)
        before = session.last_activity_at
        client.get(f"{BASE}/{sid}/status")
        assert session.last_activity_at == before
        client.get(f"{BASE}/{sid}/result")
        assert session.last_activity_at > before


def test_simultaneous_lease_attempts_only_one_owner():
    with TestClient(app) as client:
        barrier = threading.Barrier(2)
        lease = app.state.lease

        def contend():
            barrier.wait(timeout=5)
            return lease.try_acquire()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(contend) for _ in range(2)]
            owners = [future.result(timeout=10) for future in futures]
        assert sum(owner is not None for owner in owners) == 1
        assert len(app.state.store.sessions) == 0
        lease.release(next(owner for owner in owners if owner))
        assert create(client).status_code == 201
        assert len(app.state.store.sessions) == 1