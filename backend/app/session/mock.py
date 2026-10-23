"""Development-only ephemeral sample lifecycle; not the production orchestrator."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from app.core.config import Settings
from app.core.enums import Role, SessionStatus, Stage


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class MockSession:
    session_id: UUID
    role: Role
    created_at: datetime
    last_activity_at: datetime
    updated_at: datetime
    status: SessionStatus = SessionStatus.UPLOADED
    stage: Stage = Stage.UPLOAD
    error_code: str | None = None
    manual_retry_count: int = 0
    task: asyncio.Task | None = field(default=None, repr=False)

    def touch(self) -> None:
        self.last_activity_at = utcnow()


class MockStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.sessions: dict[UUID, MockSession] = {}
        self.tombstones: dict[UUID, datetime] = {}

    def cleanup(self) -> None:
        now = utcnow()
        for sid, session in list(self.sessions.items()):
            if now - session.last_activity_at >= timedelta(minutes=self.settings.SESSION_TTL_MINUTES):
                self.end(sid)
        for sid, expired_at in list(self.tombstones.items()):
            if now - expired_at >= timedelta(hours=self.settings.EXPIRED_TOMBSTONE_HOURS):
                del self.tombstones[sid]

    def create(self, role: Role, error_code: str | None) -> MockSession:
        now = utcnow()
        session = MockSession(uuid4(), role, now, now, now)
        self.sessions[session.session_id] = session
        session.task = asyncio.create_task(self.advance(session, error_code))
        return session

    async def advance(self, session: MockSession, error_code: str | None) -> None:
        try:
            await asyncio.sleep(0.05)
            if error_code:
                session.status = SessionStatus.REJECTED
                session.error_code = error_code
                session.updated_at = utcnow()
                return
            session.status = SessionStatus.VALIDATING
            session.stage = Stage.EXTRACTION
            session.updated_at = utcnow()
            await asyncio.sleep(0.05)
            session.status = SessionStatus.PROCESSING
            session.stage = Stage.RISK_ANALYSIS
            session.updated_at = utcnow()
            await asyncio.sleep(0.05)
            session.status = SessionStatus.COMPLETED
            session.stage = Stage.ASSEMBLY
            session.error_code = None
            session.updated_at = utcnow()
        except asyncio.CancelledError:
            return

    def end(self, sid: UUID) -> None:
        session = self.sessions.pop(sid, None)
        if session and session.task and not session.task.done():
            session.task.cancel()
        self.tombstones.setdefault(sid, utcnow())
