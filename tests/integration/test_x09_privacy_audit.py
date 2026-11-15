"""X-09 (N4): kiểm bảo mật — log không chứa PII/nội dung, không file tạm, metadata DB không có text.

INV-04 outbound capture nằm ở `test_pipeline_e2e.py::test_outbound_payload_is_masked_without_offsets`.
"""

import asyncio
import logging
import os
import sqlite3
import tempfile
from datetime import date
from pathlib import Path

from app.ai.dev_fake_client import DevFakeClient
from app.ai.provider import InMemoryLedger
from app.ops.metadata_db import init_db
from app.ops.quota import DailyQuota
from app.ops.runlog import RunLogWriter
from app.ops.session_ledger import SessionLedger
from app.pipeline import PipelineDeps, analyze

from tests.integration.test_pipeline_e2e import cfg, docx_bytes

SECRETS = ("0912345678", "Nguyễn Văn An", "Minh Phát", "chuyên viên kế toán", "giữ bản chính")


def _snapshot(directory: str) -> set[str]:
    return set(os.listdir(directory))


def test_pipeline_logs_and_tempdir_hold_no_contract_content(caplog, tmp_path):
    before = _snapshot(tempfile.gettempdir())
    caplog.set_level(logging.DEBUG)
    deps = PipelineDeps(cfg(), DevFakeClient(app_env="dev"), InMemoryLedger(), None, None, None, "audit")
    asyncio.run(analyze(docx_bytes(), "hd.docx", "EMPLOYEE", session_id="s", analysis_date=date(2026, 11, 13),
                        deps=deps))
    logged = "\n".join(r.getMessage() for r in caplog.records)
    for secret in SECRETS:
        assert secret not in logged
    created = _snapshot(tempfile.gettempdir()) - before
    assert not [n for n in created if n.endswith((".docx", ".pdf", ".txt"))]


def test_metadata_db_stores_numbers_only(tmp_path):
    db = init_db(str(tmp_path / "ops.sqlite3"))
    quota = DailyQuota(db, 300, 40)
    from uuid import uuid4
    ledger = SessionLedger(quota, RunLogWriter(db), uuid4())
    deps = PipelineDeps(cfg(), DevFakeClient(app_env="dev"), ledger, None, None, None, "audit")
    asyncio.run(analyze(docx_bytes(), "hd.docx", "EMPLOYEE", session_id="s", analysis_date=date(2026, 11, 13),
                        deps=deps, on_stage=ledger.enter_stage))
    ledger.close_stage()
    db.close()
    raw = Path(tmp_path / "ops.sqlite3").read_bytes()
    for secret in SECRETS:
        assert secret.encode("utf-8") not in raw
    with sqlite3.connect(tmp_path / "ops.sqlite3") as conn:
        stages = [row[0] for row in conn.execute("SELECT stage FROM run_log")]
    assert "CLAUSE_CLASSIFICATION" in stages and "RISK_ANALYSIS" in stages
