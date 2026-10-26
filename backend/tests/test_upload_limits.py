"""Mock upload admission/rejection behavior (not production quota or parsing)."""

import os
import time
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "dev")

from app.main import app  # noqa: E402


URL = "/api/v1/sessions"
PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def upload(client, *, role="EMPLOYEE", filename="contract.pdf", content=PDF):
    data = {} if role is None else {"role": role}
    return client.post(URL, data=data, files={"file": (filename, content, "application/pdf")})


def rejected_status(client, session_id, expected_code):
    deadline = time.monotonic() + 3
    while True:
        response = client.get(f"{URL}/{session_id}/status")
        assert response.status_code == 200, response.text
        status = response.json()
        if status["status"] == "REJECTED":
            assert status["error_code"] == expected_code
            return
        assert time.monotonic() < deadline, status
        time.sleep(0.01)


@pytest.mark.parametrize("role", [None, "INVALID", ""])
def test_missing_or_invalid_role_is_rejected_before_creating_session(client, role):
    response = upload(client, role=role)
    assert response.status_code == 400, response.text
    assert response.json()["error"]["code"] == "ROLE_REQUIRED"
    assert "session_id" not in response.json()


@pytest.mark.parametrize(
    ("filename", "content", "error_code"),
    [
        ("contract.txt", PDF, "UNSUPPORTED_FILE_TYPE"),
        ("contract.pdf", b"not a pdf", "UNSUPPORTED_FILE_TYPE"),
        ("contract.docx", b"not a zip", "UNSUPPORTED_FILE_TYPE"),
        ("contract.pdf", "oversized", "FILE_TOO_LARGE"),
    ],
)
def test_bad_upload_is_rejected_as_session_after_201(client, filename, content, error_code):
    if content == "oversized":
        content = PDF + b"x" * (10 * 1024 * 1024)
    response = upload(client, filename=filename, content=content)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "UPLOADED"
    assert UUID(body["session_id"]).version == 4
    rejected_status(client, body["session_id"], error_code)
    result = client.get(f"{URL}/{body['session_id']}/result")
    assert result.status_code == 409
    assert result.json()["error"]["code"] == "SESSION_REJECTED"
