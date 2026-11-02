"""Admission reserve and actual provider-call accounting (implements `CallLedger`)."""
from datetime import datetime, timezone

from app.domain.errors import AiProviderError
from app.ops.metadata_db import MetadataDB


def _today(now: datetime | None) -> str:
    return (now or datetime.now(timezone.utc)).date().isoformat()


class DailyQuota:
    def __init__(self, db: MetadataDB, quota: int | None, reserve: int | None):
        self.db = db
        self.quota = quota
        self.reserve = reserve

    def admit_new_session(self, now: datetime | None = None) -> bool:
        if self.quota is None or self.reserve is None:
            return True
        return self.db.remaining(_today(now), self.quota) >= self.reserve

    def before_call(self, now: datetime | None = None) -> None:
        """Giữ chỗ một request provider (kể cả retry). Hết quota ngày ⇒ AI_PROVIDER_ERROR, KHÔNG gửi."""
        if not self.db.try_reserve(_today(now), self.quota):
            raise AiProviderError("QUOTA_EXHAUSTED")

    def after_call(self, in_tokens: int, out_tokens: int, cost: float, error_code: str | None = None,
                   now: datetime | None = None) -> None:
        """Ghi usage thực tế (token, chi phí ước tính, lỗi) — kể cả khi request lỗi."""
        self.db.add_usage(_today(now), in_tokens, out_tokens, cost, error_code is not None)
