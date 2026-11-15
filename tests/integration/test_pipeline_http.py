"""X-19 qua HTTP: upload DOCX thật → pipeline (provider giả) → status/result/export/End.

INV-09: dữ liệu phiên chỉ ở RAM, End/restart xóa nội dung. INV-10: FAILED không trả kết quả; Retry giai đoạn AI
chạy tiếp từ CLAUSE_CLASSIFICATION với artifact cục bộ giữ trong RAM.
"""

import os
import time

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "dev")

from app.ai.dev_fake_client import DevFakeClient  # noqa: E402
from app.ai.provider import InMemoryLedger  # noqa: E402
from app.domain.errors import AiTimeout  # noqa: E402
from app.main import app, load_legal, settings  # noqa: E402
from app.pipeline import PipelineDeps  # noqa: E402
from app.session.orchestrator import make_pipeline_runner  # noqa: E402

from tests.integration.test_pipeline_e2e import cfg, docx_bytes  # noqa: E402

URL = "/api/v1/sessions"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class Flaky:
    """Lỗi ở LLM #2 lần đầu, sau đó bình thường; đếm request theo loại."""

    def __init__(self, fail_times=1):
        self.inner, self.fail_times, self.kinds = DevFakeClient(app_env="dev"), fail_times, []

    async def generate_structured(self, *, model_id, messages, response_schema, timeout_s):
        import json
        kind = json.loads(messages[1]["content"])["schema_version"]
        self.kinds.append(kind)
        if kind.startswith("risk_analysis") and self.fail_times > 0:
            self.fail_times -= 1
            raise AiTimeout()
        return await self.inner.generate_structured(model_id=model_id, messages=messages,
                                                    response_schema=response_schema, timeout_s=timeout_s)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def use_pipeline(client, provider):
    legal = load_legal(settings.model_copy(update={"APP_ENV": "dev"}))
    runner = make_pipeline_runner(lambda s: PipelineDeps(cfg(), provider, InMemoryLedger(), *legal, "http-test"))
    client.app.state.orchestrator.runner = runner
    client.app.state.pipeline_enabled = True


def create(client, content=None, name="hd.docx", role="EMPLOYEE"):
    r = client.post(URL, data={"role": role}, files={"file": (name, content or docx_bytes(), DOCX)})
    assert r.status_code == 201, r.text
    return r.json()["session_id"]


def wait(client, sid, until=("COMPLETED", "FAILED", "REJECTED")):
    deadline = time.monotonic() + 10
    while True:
        st = client.get(f"{URL}/{sid}/status").json()
        if st["status"] in until:
            return st
        assert time.monotonic() < deadline, st
        time.sleep(0.02)


def test_upload_runs_real_pipeline_and_exports(client):
    use_pipeline(client, DevFakeClient(app_env="dev"))
    sid = create(client)
    st = wait(client, sid)
    assert st["status"] == "COMPLETED", st
    result = client.get(f"{URL}/{sid}/result").json()
    assert result["version_pins"]["app_commit"] == "http-test"
    assert "giữ bản chính văn bằng" in result["canonical_text"]   # phân tích đúng file upload, không phải fixture
    assert client.get(f"{URL}/{sid}/export?format=docx").status_code == 200
    session = client.app.state.store.get(__import__("uuid").UUID(sid))
    assert session.upload is None                                   # bytes bị xóa sau COMPLETED
    assert client.delete(f"{URL}/{sid}").json()["status"] == "EXPIRED"
    assert client.get(f"{URL}/{sid}/result").status_code in (404, 410)


def test_rejected_upload_is_terminal(client):
    use_pipeline(client, DevFakeClient(app_env="dev"))
    sid = create(client, docx_bytes(["HỢP ĐỒNG MUA BÁN", "Bên bán giao hàng cho bên mua theo đơn hàng. " * 5]))
    st = wait(client, sid)
    assert (st["status"], st["error_code"]) == ("REJECTED", "NOT_LABOR_CONTRACT")
    assert client.post(f"{URL}/{sid}/retry").status_code == 409


def test_failed_has_no_result_and_retry_resumes_ai_stage(client, monkeypatch):
    import app.pipeline as pipeline
    extractions = []
    real_extract = pipeline.extract_bytes
    monkeypatch.setattr(pipeline, "extract_bytes", lambda *a, **k: extractions.append(1) or real_extract(*a, **k))
    provider = Flaky()
    use_pipeline(client, provider)
    sid = create(client)
    st = wait(client, sid)
    assert (st["status"], st["error_code"], st["stage"]) == ("FAILED", "AI_TIMEOUT", "RISK_ANALYSIS")
    r = client.get(f"{URL}/{sid}/result")                            # INV-10
    assert r.status_code == 409 and r.json()["error"]["code"] == "SESSION_NOT_READY"
    retry = client.post(f"{URL}/{sid}/retry")
    assert retry.status_code == 200 and retry.json()["status"] == "PROCESSING"
    assert retry.json()["stage"] == "CLAUSE_CLASSIFICATION"
    st = wait(client, sid)
    assert st["status"] == "COMPLETED" and st["manual_retry_count"] == 1
    # Retry chạy lại LLM #1 + #2 nhưng KHÔNG trích xuất lại (resume artifact cục bộ trong RAM).
    kinds = [k.split("_")[0] for k in provider.kinds]
    assert kinds.count("clause") == 2 and kinds[0] == "clause"
    assert len(extractions) == 1


def test_restart_loses_session_content(client):
    use_pipeline(client, DevFakeClient(app_env="dev"))
    sid = create(client)
    wait(client, sid)
    client.__exit__(None, None, None)                                # shutdown: End mọi phiên (INV-09)
    with TestClient(app) as fresh:
        r = fresh.get(f"{URL}/{sid}/result")
        assert r.status_code in (404, 410)
        assert "canonical_text" not in r.text
