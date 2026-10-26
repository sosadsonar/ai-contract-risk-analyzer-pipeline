"""Persistent sliding-window admission with pseudonymous IP keys."""
import hashlib
import hmac
from datetime import datetime

from app.ops.metadata_db import MetadataDB


class SlidingWindowLimiter:
    def __init__(self, db: MetadataDB, salt: str, limit: int = 5, window_seconds: int = 600):
        self.db = db
        self.salt = salt.encode()
        self.limit = limit
        self.window_seconds = window_seconds

    def check_and_record(self, ip: str, now: datetime) -> bool:
        key = hmac.new(self.salt, ip.encode(), hashlib.sha256).hexdigest()[:32]
        return self.db.rate_check(key, now, self.limit, self.window_seconds)
