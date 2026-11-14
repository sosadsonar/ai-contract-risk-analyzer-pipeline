"""Ledger theo phiên: chuyển tiếp mọi request tới quota ngày (C-16) và ghi RunLog theo stage (OI-05 §2.4 mục 3).

RunLog chỉ chứa số (calls, token, cost, thời lượng, mã lỗi) — không text/tên file/prompt (INV-13).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from app.core.enums import Stage


@dataclass
class _Counter:
    calls: int = 0
    in_tokens: int = 0
    out_tokens: int = 0
    cost: float = 0.0


@dataclass
class SessionLedger:
    quota: object  # DailyQuota (CallLedger)
    runlog: Optional[object] = None  # RunLogWriter
    session_id: Optional[UUID] = None
    total: _Counter = field(default_factory=_Counter)
    _stage: Optional[Stage] = None
    _stage_started: Optional[datetime] = None
    _stage_t0: float = 0.0
    _stage_counter: _Counter = field(default_factory=_Counter)

    def before_call(self) -> None:
        self.quota.before_call()
        self.total.calls += 1
        self._stage_counter.calls += 1

    def after_call(self, in_tokens, out_tokens, cost, error_code=None) -> None:
        self.quota.after_call(in_tokens, out_tokens, cost, error_code)
        for c in (self.total, self._stage_counter):
            c.in_tokens += in_tokens
            c.out_tokens += out_tokens
            c.cost += cost

    def enter_stage(self, stage: Stage) -> None:
        self.close_stage()
        self._stage = stage
        self._stage_started = datetime.now(timezone.utc)
        self._stage_t0 = time.perf_counter()
        self._stage_counter = _Counter()

    def close_stage(self, error_code: Optional[str] = None) -> None:
        if self._stage is None or self.runlog is None or self.session_id is None:
            self._stage = None
            return
        c = self._stage_counter
        self.runlog.record_stage(self.session_id, self._stage, self._stage_started,
                                 int((time.perf_counter() - self._stage_t0) * 1000), c.calls, c.in_tokens,
                                 c.out_tokens, float(c.cost), error_code)
        self._stage = None
