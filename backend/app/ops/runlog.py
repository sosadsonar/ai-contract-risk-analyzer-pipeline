"""Persistent stage metrics only: no document text, prompt, filename or provider payload."""

import math
from datetime import datetime, timezone
from uuid import UUID

from app.core.enums import Stage
from app.ops.metadata_db import MetadataDB

_ERROR_CODES = frozenset({
    "UNSUPPORTED_FILE_TYPE", "FILE_TOO_LARGE", "PDF_PAGE_LIMIT_EXCEEDED",
    "DOCX_TEXT_LIMIT_EXCEEDED", "NO_EXTRACTABLE_TEXT", "UNSUPPORTED_TEXT_ENCODING",
    "NOT_LABOR_CONTRACT", "TOO_MANY_CLAUSES", "AI_TIMEOUT", "AI_PROVIDER_ERROR",
    "AI_OUTPUT_INVALID", "INTERNAL_ERROR",
})


def _nonnegative_int(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


def _nonnegative_cost(value):
    if type(value) not in (float, int) or not math.isfinite(value) or value < 0:
        raise ValueError("estimated_cost must be finite and non-negative")


class RunLogWriter:
    def __init__(self, db: MetadataDB):
        self.db = db

    def record_stage(self, session_id: UUID, stage: Stage, started_at: datetime,
                     duration_ms: int, calls: int, in_tokens: int, out_tokens: int,
                     cost: float, error_code: str | None = None,
                     graph_enabled: bool | None = None,
                     graph_added_candidates: int | None = None) -> None:
        """Reject arbitrary strings before they can enter the operational database."""
        if not isinstance(session_id, UUID) or session_id.version != 4:
            raise ValueError("session_id must be a UUIDv4")
        if not isinstance(stage, Stage):
            raise ValueError("stage must be a Stage")
        if not isinstance(started_at, datetime) or started_at.tzinfo is None or started_at.utcoffset() is None:
            raise ValueError("started_at must be timezone-aware")
        for value, name in ((duration_ms, "duration_ms"), (calls, "calls"),
                            (in_tokens, "in_tokens"), (out_tokens, "out_tokens")):
            _nonnegative_int(value, name)
        _nonnegative_cost(cost)
        if error_code is not None and (not isinstance(error_code, str) or error_code not in _ERROR_CODES):
            raise ValueError("error_code must be a documented stage code")
        if graph_enabled is not None and type(graph_enabled) is not bool:
            raise ValueError("graph_enabled must be a boolean or None")
        if graph_added_candidates is not None:
            _nonnegative_int(graph_added_candidates, "graph_added_candidates")
        self.db.insert_run_log(str(session_id), stage.value,
                               started_at.astimezone(timezone.utc).isoformat(), duration_ms,
                               calls, in_tokens, out_tokens, float(cost), error_code,
                               graph_enabled, graph_added_candidates)
