"""SessionLedger: chuyển tiếp quota + RunLog theo stage chỉ chứa số (OI-05 §2.4 mục 3)."""

from uuid import uuid4

from app.core.enums import Stage
from app.ops.session_ledger import SessionLedger


class Quota:
    def __init__(self):
        self.events = []

    def before_call(self):
        self.events.append("before")

    def after_call(self, i, o, c, e=None):
        self.events.append(("after", i, o, c, e))


class RunLog:
    def __init__(self):
        self.rows = []

    def record_stage(self, sid, stage, started, ms, calls, i, o, cost, code):
        self.rows.append((stage, calls, i, o, cost, code))


def test_counts_per_stage_and_total():
    quota, log = Quota(), RunLog()
    ledger = SessionLedger(quota, log, uuid4())
    ledger.enter_stage(Stage.CLAUSE_CLASSIFICATION)
    ledger.before_call()
    ledger.after_call(100, 20, 0.01)
    ledger.enter_stage(Stage.RISK_ANALYSIS)
    ledger.before_call()
    ledger.after_call(50, 5, 0.0, "timeout")
    ledger.before_call()
    ledger.after_call(60, 6, 0.0)
    ledger.close_stage("AI_TIMEOUT")
    assert log.rows == [(Stage.CLAUSE_CLASSIFICATION, 1, 100, 20, 0.01, None),
                        (Stage.RISK_ANALYSIS, 2, 110, 11, 0.0, "AI_TIMEOUT")]
    assert (ledger.total.calls, ledger.total.in_tokens) == (3, 210)
    assert quota.events.count("before") == 3
