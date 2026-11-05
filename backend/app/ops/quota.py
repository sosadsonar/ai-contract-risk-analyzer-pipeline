"""Admission reserve and actual provider-call accounting (implements CallLedger)."""
import csv
import math
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from uuid import uuid4

from app.ops.metadata_db import MetadataDB


def _today(now: datetime | None) -> str:
    return (now or datetime.now(timezone.utc)).date().isoformat()


def _usage_values(in_tokens: int, out_tokens: int, cost: float) -> None:
    if type(in_tokens) is not int or in_tokens < 0 or type(out_tokens) is not int or out_tokens < 0:
        raise ValueError("token counts must be non-negative integers")
    if type(cost) not in (int, float) or not math.isfinite(cost) or cost < 0:
        raise ValueError("cost must be finite and non-negative")


def _safe_error_code(code: str | None) -> str:
    if code is None:
        return ""
    if not isinstance(code, str):
        return "INTERNAL_ERROR"
    if code in {"timeout", "network", "invalid_json", "schema_invalid", "cancelled", "INTERNAL_ERROR"}:
        return code
    if code.startswith("http:") and len(code) == 8 and code[5:].isdigit():
        return code
    return "INTERNAL_ERROR"


class DailyQuota:
    def __init__(self, db: MetadataDB, quota: int | None, reserve: int | None):
        self.db = db
        self.quota = quota
        self.reserve = reserve
        self._pending_day: ContextVar[str | None] = ContextVar("daily_quota_request_day", default=None)

    def admit_new_session(self, now: datetime | None = None) -> bool:
        if self.quota is None or self.reserve is None:
            return True
        return self.db.remaining(_today(now), self.quota) >= self.reserve

    def before_call(self, now: datetime | None = None) -> None:
        """Atomically count each request before sending; only admission enforces the reserve."""
        if self._pending_day.get() is not None:
            raise RuntimeError("Previous request is missing after_call")
        day = _today(now)
        self.db.increment(day)
        self._pending_day.set(day)

    def after_call(self, in_tokens: int, out_tokens: int, cost: float, error_code: str | None = None,
                   now: datetime | None = None) -> None:
        """Record actual usage on the request's original UTC day, even across midnight."""
        day = self._pending_day.get()
        if day is None:
            raise RuntimeError("after_call requires a preceding before_call")
        _usage_values(in_tokens, out_tokens, cost)
        self.db.add_usage(day, in_tokens, out_tokens, cost, error_code is not None)
        self._pending_day.set(None)


class EvalCostLedger:
    """Standalone CSV ledger for offline evaluation; never touches product quota/SQLite."""

    _COLUMNS = ("event", "request_id", "at_utc", "input_tokens", "output_tokens",
                "estimated_cost", "error_code")

    def __init__(self, path: Path, *, app_env: str):
        if app_env != "eval":
            raise ValueError("EvalCostLedger is only available in eval")
        self.path = Path(path)
        if self.path.suffix != ".csv":
            raise ValueError("EvalCostLedger requires a separate .csv file")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._pending: ContextVar[str | None] = ContextVar("eval_request_id", default=None)
        with self.path.open("a+", encoding="utf-8", newline="") as stream:
            stream.seek(0)
            first = next(csv.reader(stream), None)
            if first is None:
                csv.writer(stream).writerow(self._COLUMNS)
            elif tuple(first) != self._COLUMNS:
                raise ValueError("EvalCostLedger file has an incompatible header")

    def _append(self, event: str, request_id: str, in_tokens: int = 0,
                out_tokens: int = 0, cost: float = 0.0, error_code: str = "") -> None:
        with self._lock, self.path.open("a", encoding="utf-8", newline="") as stream:
            csv.writer(stream).writerow((event, request_id, datetime.now(timezone.utc).isoformat(),
                                         in_tokens, out_tokens, cost, error_code))

    def before_call(self) -> None:
        if self._pending.get() is not None:
            raise RuntimeError("Previous evaluation request is missing after_call")
        request_id = str(uuid4())
        self._append("started", request_id)  # durable attempt record BEFORE sending
        self._pending.set(request_id)

    def after_call(self, in_tokens: int, out_tokens: int, cost: float,
                   error_code: str | None = None) -> None:
        request_id = self._pending.get()
        if request_id is None:
            raise RuntimeError("after_call requires a preceding before_call")
        _usage_values(in_tokens, out_tokens, cost)
        self._append("finished", request_id, in_tokens, out_tokens, cost, _safe_error_code(error_code))
        self._pending.set(None)

    def summary(self) -> dict:
        """Count attempts (including unfinished ones) and actual completed usage."""
        result = {"calls": 0, "completed": 0, "input_tokens": 0,
                  "output_tokens": 0, "estimated_cost": 0.0, "errors": 0}
        with self._lock, self.path.open("r", encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream):
                if row["event"] == "started":
                    result["calls"] += 1
                elif row["event"] == "finished":
                    result["completed"] += 1
                    result["input_tokens"] += int(row["input_tokens"])
                    result["output_tokens"] += int(row["output_tokens"])
                    result["estimated_cost"] += float(row["estimated_cost"])
                    result["errors"] += bool(row["error_code"])
        return result
