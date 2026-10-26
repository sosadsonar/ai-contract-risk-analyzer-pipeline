"""Ephemeral session content; only expiry tombstones survive process restart."""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from uuid import UUID, uuid4

from app.core.enums import Role, SessionStatus, Stage


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Session:
    session_id: UUID
    role: Role
    created_at: datetime
    updated_at: datetime
    last_activity_at: datetime
    analysis_date: str
    status: SessionStatus = SessionStatus.UPLOADED
    stage: Stage = Stage.UPLOAD
    failed_stage: Stage | None = None
    error_code: str | None = None
    manual_retry_count: int = 0
    task: asyncio.Task | None = field(default=None, repr=False)
    result: dict | None = field(default=None, repr=False)
    cancelled: bool = False


class InMemorySessionStore:
    def __init__(self, metadata=None):
        self.sessions: dict[UUID, Session] = {}
        self.metadata = metadata
        self.lock = RLock()

    def create(self, role: Role, now: datetime | None = None) -> Session:
        now = now or utcnow()
        session = Session(uuid4(), role, now, now, now, now.date().isoformat())
        with self.lock:
            self.sessions[session.session_id] = session
        return session

    def get(self, sid: UUID) -> Session | None:
        with self.lock:
            return self.sessions.get(sid)

    def touch(self, sid: UUID, now: datetime | None = None) -> None:
        with self.lock:
            session = self.sessions.get(sid)
            if session:
                session.last_activity_at = now or utcnow()

    def delete(self, sid: UUID) -> Session | None:
        with self.lock:
            return self.sessions.pop(sid, None)

    def expired(self, cutoff: datetime) -> list[UUID]:
        with self.lock:
            return [sid for sid, session in self.sessions.items() if session.last_activity_at <= cutoff]
