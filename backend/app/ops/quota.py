"""Admission reserve and actual provider-call accounting."""
from datetime import datetime, timezone

from app.ops.metadata_db import MetadataDB


class DailyQuota:
    def __init__(self, db: MetadataDB, quota: int | None, reserve: int | None):
        self.db = db
        self.quota = quota
        self.reserve = reserve

    def admit_new_session(self, now: datetime | None = None) -> bool:
        if self.quota is None or self.reserve is None:
            return True
        today = (now or datetime.now(timezone.utc)).date().isoformat()
        return self.db.remaining(today, self.quota) >= self.reserve

    def before_call(self, now: datetime | None = None) -> None:
        today = (now or datetime.now(timezone.utc)).date().isoformat()
        self.db.increment(today)
