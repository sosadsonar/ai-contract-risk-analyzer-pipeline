"""Sole authority for session status transitions and cancellation."""
import asyncio
from datetime import datetime
from uuid import UUID

from app.core.enums import SessionStatus, Stage
from app.session.lock import ProcessingLease
from app.session.mock import sample_result
from app.session.store import InMemorySessionStore, Session, utcnow

_LOCAL = {Stage.UPLOAD, Stage.EXTRACTION, Stage.SCOPE_PRECHECK, Stage.PII_MASKING,
          Stage.SEGMENTATION, Stage.CLAUSE_GRAPH}
_ALLOWED = {
    SessionStatus.UPLOADED: {SessionStatus.VALIDATING},
    SessionStatus.VALIDATING: {SessionStatus.REJECTED, SessionStatus.FAILED, SessionStatus.PROCESSING},
    SessionStatus.PROCESSING: {SessionStatus.COMPLETED, SessionStatus.FAILED},
    SessionStatus.FAILED: {SessionStatus.VALIDATING, SessionStatus.PROCESSING, SessionStatus.EXPIRED},
    SessionStatus.COMPLETED: {SessionStatus.EXPIRED},
    SessionStatus.REJECTED: {SessionStatus.EXPIRED},
}


class Orchestrator:
    def __init__(self, store: InMemorySessionStore, lease: ProcessingLease):
        self.store = store
        self.lease = lease

    def transition(self, session: Session, status: SessionStatus, stage: Stage,
                   error_code: str | None = None, result: dict | None = None) -> bool:
        with self.store.lock:
            if self.store.sessions.get(session.session_id) is not session or session.cancelled:
                return False
            if status not in _ALLOWED.get(session.status, set()):
                raise ValueError(f"Invalid transition {session.status} -> {status}")
            session.status = status
            session.stage = stage
            session.error_code = error_code
            session.failed_stage = stage if status == SessionStatus.FAILED else None
            session.result = result if status == SessionStatus.COMPLETED else None
            session.updated_at = utcnow()
            return True

    def start(self, session: Session, error_code: str | None = None) -> None:
        session.task = asyncio.create_task(self.run(session, error_code))

    async def run(self, session: Session, error_code: str | None = None) -> None:
        try:
            if session.status == SessionStatus.UPLOADED:
                if not self.transition(session, SessionStatus.VALIDATING, Stage.EXTRACTION):
                    return
            await asyncio.sleep(0.05)
            if error_code:
                self.transition(session, SessionStatus.REJECTED, Stage.EXTRACTION, error_code)
                return
            if session.status == SessionStatus.VALIDATING:
                if not self.transition(session, SessionStatus.PROCESSING, Stage.RISK_ANALYSIS):
                    return
            await asyncio.sleep(0.05)
            result = sample_result(session)
            self.transition(session, SessionStatus.COMPLETED, Stage.ASSEMBLY, result=result)
        except asyncio.CancelledError:
            raise
        except Exception:
            if self.store.get(session.session_id) is session and not session.cancelled:
                stage = session.stage
                if session.status in (SessionStatus.VALIDATING, SessionStatus.PROCESSING):
                    self.transition(session, SessionStatus.FAILED, stage, "INTERNAL_ERROR")
        finally:
            self.lease.release(session.session_id)

    def retry(self, session: Session) -> bool:
        if session.status != SessionStatus.FAILED or session.manual_retry_count >= 2:
            return False
        if self.lease.try_acquire(session.session_id) is None:
            return False
        try:
            with self.store.lock:
                if session.cancelled or self.store.get(session.session_id) is not session:
                    return False
                target = SessionStatus.VALIDATING if session.failed_stage in _LOCAL else SessionStatus.PROCESSING
                stage = Stage.EXTRACTION if target == SessionStatus.VALIDATING else Stage.RISK_ANALYSIS
                self.transition(session, target, stage)
                session.manual_retry_count += 1
                self.start(session)
                return True
        finally:
            if session.task is None or session.task.done():
                self.lease.release(session.session_id)

    def end(self, sid: UUID, now: datetime | None = None) -> bool:
        now = now or utcnow()
        with self.store.lock:
            session = self.store.get(sid)
            if session is None:
                return False
            session.cancelled = True
            session.status = SessionStatus.EXPIRED
            session.updated_at = now
            self.store.delete(sid)
            session.result = None
            if session.task and not session.task.done():
                session.task.cancel()
            self.lease.release(sid)
            if self.store.metadata:
                self.store.metadata.add_tombstone(sid, now)
            return True
