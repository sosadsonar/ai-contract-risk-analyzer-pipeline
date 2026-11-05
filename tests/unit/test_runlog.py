"""RunLog stores stage metrics, not contract content or arbitrary error strings."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from app.core.enums import Stage
from app.ops.metadata_db import MetadataDB
from app.ops.runlog import RunLogWriter

START = datetime(2026, 11, 2, 10, tzinfo=timezone.utc)


def test_stage_metrics_persist_with_only_bounded_operational_fields(tmp_path):
    path = tmp_path / "ops.sqlite3"
    db = MetadataDB(str(path))
    writer = RunLogWriter(db)
    session_id = uuid4()
    writer.record_stage(session_id, Stage.LEGAL_RETRIEVAL, START, 37, 2, 400, 50, 0.012,
                        graph_enabled=True, graph_added_candidates=3)
    row = db.connection.execute(
        "SELECT session_id,stage,started_at,duration_ms,calls,input_tokens,output_tokens,"
        "estimated_cost,error_code,graph_enabled,graph_added_candidates FROM run_log"
    ).fetchone()
    assert row == (str(session_id), "LEGAL_RETRIEVAL", "2026-11-02T10:00:00+00:00",
                   37, 2, 400, 50, 0.012, None, 1, 3)
    db.close()


@pytest.mark.parametrize("bad", ["raw contract content 0912345678", "http:500",
                                 "AI_TIMEOUT\nprivate filename", "NGUYENVANA"])
def test_arbitrary_error_text_cannot_be_persisted(tmp_path, bad):
    path = tmp_path / "ops.sqlite3"
    db = MetadataDB(str(path))
    writer = RunLogWriter(db)
    with pytest.raises(ValueError, match="error_code"):
        writer.record_stage(uuid4(), Stage.RISK_ANALYSIS, START, 20, 1, 0, 0, 0.0, bad)
    assert db.connection.execute("SELECT COUNT(*) FROM run_log").fetchone()[0] == 0
    db.close()
    assert "0912345678" not in path.read_bytes().decode("utf-8", errors="ignore")


def test_concurrent_stage_writes_do_not_lose_records(tmp_path):
    db = MetadataDB(str(tmp_path / "ops.sqlite3"))
    writer = RunLogWriter(db)
    sid = uuid4()
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda i: writer.record_stage(sid, Stage.EXTRACTION, START, i, 0, 0, 0, 0.0), range(32)))
    durations = [row[0] for row in db.connection.execute("SELECT duration_ms FROM run_log ORDER BY duration_ms")]
    assert durations == list(range(32))
    db.close()
