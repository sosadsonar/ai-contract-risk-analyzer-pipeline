"""Sole authority for session status transitions and cancellation.

Hai chế độ (X-19):
  * `runner` = None  — dev sample: trả fixture `final_result_v1` (chỉ APP_ENV=dev khi không cấu hình provider).
  * `runner` có      — pipeline thật (`app.pipeline.analyze`) cho mọi file upload; demo/eval luôn dùng chế độ này.

Ánh xạ lỗi: ValidationReject ⇒ REJECTED(code) (cuối, không retry); AI_* / INTERNAL_ERROR ⇒ FAILED(code,
failed_stage) (Retry ≤ 2); StageCancelled ⇒ không đổi gì (End đã xử lý). FAILED không bao giờ giữ kết quả (INV-10).
Retry: failed_stage cục bộ ⇒ VALIDATING chạy lại từ EXTRACTION; failed_stage AI ⇒ PROCESSING tiếp từ
CLAUSE_CLASSIFICATION với artifact cục bộ giữ trong RAM nếu version pin còn khớp (stage resume, cut item 2).
"""
import asyncio
from datetime import date, datetime
from typing import Awaitable, Callable, Optional
from uuid import UUID

from app.core.enums import SessionStatus, Stage
from app.domain.errors import StageCancelled, ValidationReject
from app.session.lock import ProcessingLease
from app.session.mock import sample_result
from app.session.store import InMemorySessionStore, Session, utcnow

_LOCAL = {Stage.UPLOAD, Stage.EXTRACTION, Stage.SCOPE_PRECHECK, Stage.PII_MASKING,
          Stage.SEGMENTATION, Stage.CLAUSE_GRAPH}
_AI = {Stage.CLAUSE_CLASSIFICATION, Stage.LEGAL_RETRIEVAL, Stage.RISK_ANALYSIS,
       Stage.CITATION_VALIDATION, Stage.ASSEMBLY}
_ALLOWED = {
    SessionStatus.UPLOADED: {SessionStatus.VALIDATING},
    # X-20: End/cleanup có thể kết thúc phiên đang chạy → VALIDATING/PROCESSING → EXPIRED hợp lệ.
    SessionStatus.VALIDATING: {SessionStatus.REJECTED, SessionStatus.FAILED, SessionStatus.PROCESSING,
                               SessionStatus.EXPIRED},
    SessionStatus.PROCESSING: {SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.EXPIRED},
    SessionStatus.FAILED: {SessionStatus.VALIDATING, SessionStatus.PROCESSING, SessionStatus.EXPIRED},
    SessionStatus.COMPLETED: {SessionStatus.EXPIRED},
    SessionStatus.REJECTED: {SessionStatus.EXPIRED},
}

# runner(session, on_stage, check_cancel) -> final_result dict; raise ValidationReject/AI*/StageCancelled.
Runner = Callable[[Session, Callable[[Stage], None], Callable[[], bool]], Awaitable[dict]]


class Orchestrator:
    def __init__(self, store: InMemorySessionStore, lease: ProcessingLease, runner: Optional[Runner] = None):
        self.store = store
        self.lease = lease
        self.runner = runner

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

    def set_stage(self, session: Session, stage: Stage) -> None:
        """Đổi stage trong cùng status; VALIDATING → PROCESSING khi bước vào stage AI đầu tiên."""
        with self.store.lock:
            if self.store.sessions.get(session.session_id) is not session or session.cancelled:
                raise StageCancelled()
            if stage in _AI and session.status == SessionStatus.VALIDATING:
                self.transition(session, SessionStatus.PROCESSING, stage)
                return
            session.stage = stage
            session.updated_at = utcnow()

    def start(self, session: Session, error_code: str | None = None) -> None:
        session.task = asyncio.create_task(self.run(session, error_code))

    async def run(self, session: Session, error_code: str | None = None) -> None:
        try:
            if session.status == SessionStatus.UPLOADED:
                if not self.transition(session, SessionStatus.VALIDATING, Stage.EXTRACTION):
                    return
            if error_code:
                await asyncio.sleep(0)
                self.transition(session, SessionStatus.REJECTED, Stage.EXTRACTION, error_code)
                session.upload = None
                return
            if self.runner is None:
                await self._run_sample(session)
                return
            result = await self.runner(session, lambda stage: self.set_stage(session, stage),
                                       lambda: session.cancelled)
            if self.transition(session, SessionStatus.COMPLETED, Stage.ASSEMBLY, result=result):
                session.upload = None
                session.resume = None
        except asyncio.CancelledError:
            raise
        except StageCancelled:
            return
        except ValidationReject as exc:
            if self.store.get(session.session_id) is session and not session.cancelled:
                self.transition(session, SessionStatus.REJECTED, session.stage, exc.code)
                session.upload = None
        except Exception as exc:  # noqa: BLE001 — mọi lỗi khác ⇒ FAILED với mã ổn định, không lộ message
            if self.store.get(session.session_id) is session and not session.cancelled:
                if session.status in (SessionStatus.VALIDATING, SessionStatus.PROCESSING):
                    code = getattr(exc, "code", "INTERNAL_ERROR")
                    if code not in ("AI_TIMEOUT", "AI_PROVIDER_ERROR", "AI_OUTPUT_INVALID"):
                        code = "INTERNAL_ERROR"
                    self.transition(session, SessionStatus.FAILED, session.stage, code)
        finally:
            self.lease.release(session.session_id)

    async def _run_sample(self, session: Session) -> None:
        await asyncio.sleep(0.05)
        if session.status == SessionStatus.VALIDATING:
            if not self.transition(session, SessionStatus.PROCESSING, Stage.RISK_ANALYSIS):
                return
        await asyncio.sleep(0.05)
        result = sample_result(session)
        self.transition(session, SessionStatus.COMPLETED, Stage.ASSEMBLY, result=result)

    def retry(self, session: Session) -> bool:
        if session.status != SessionStatus.FAILED or session.manual_retry_count >= 2:
            return False
        if self.lease.try_acquire(session.session_id) is None:
            return False
        try:
            with self.store.lock:
                if session.cancelled or self.store.get(session.session_id) is not session:
                    return False
                local = session.failed_stage in _LOCAL or session.resume is None
                target = SessionStatus.VALIDATING if local else SessionStatus.PROCESSING
                if self.runner is None:  # dev sample giữ hành vi cũ
                    target = SessionStatus.VALIDATING if session.failed_stage in _LOCAL else SessionStatus.PROCESSING
                    stage = Stage.EXTRACTION if target == SessionStatus.VALIDATING else Stage.RISK_ANALYSIS
                else:
                    if local:
                        session.resume = None
                    stage = Stage.EXTRACTION if local else Stage.CLAUSE_CLASSIFICATION
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


def make_pipeline_runner(deps_factory, analysis_date_of: Callable[[Session], date] | None = None) -> Runner:
    """Runner gọi `app.pipeline.analyze`; `deps_factory(session)` trả PipelineDeps (ledger theo phiên).

    Nếu `deps.ledger` có `enter_stage`/`close_stage` (SessionLedger) thì RunLog được ghi theo từng stage."""
    from app.pipeline import PipelineArtifacts, analyze, resume_state

    async def runner(session: Session, on_stage, check_cancel) -> dict:
        if session.upload is None:
            raise ValidationReject("UNSUPPORTED_FILE_TYPE")
        deps = deps_factory(session)
        ledger = deps.ledger
        art = PipelineArtifacts()
        resume = session.resume
        session.resume = None

        def stage_hook(stage: Stage) -> None:
            if hasattr(ledger, "enter_stage"):
                ledger.enter_stage(stage)
            on_stage(stage)

        try:
            art = await analyze(session.upload, session.display_name or "", session.role,
                                session_id=str(session.session_id),
                                analysis_date=(analysis_date_of(session) if analysis_date_of
                                               else date.fromisoformat(session.analysis_date)),
                                deps=deps, on_stage=stage_hook, check_cancel=check_cancel,
                                resume=resume, into=art)
        except ValidationReject as exc:
            _close(ledger, exc.code)
            raise
        except StageCancelled:
            _close(ledger, None)
            raise
        except Exception as exc:
            code = getattr(exc, "code", "INTERNAL_ERROR")
            _close(ledger, code if code in ("AI_TIMEOUT", "AI_PROVIDER_ERROR", "AI_OUTPUT_INVALID") else "INTERNAL_ERROR")
            source = resume.artifacts if resume is not None and resume.matches(deps) else art
            session.resume = resume_state(source, deps)
            raise
        _close(ledger, None)
        return art.final_result

    def _close(ledger, code):
        if hasattr(ledger, "close_stage"):
            try:
                ledger.close_stage(code)
            except ValueError:  # mã lỗi ngoài danh mục RunLog: không để logging làm hỏng luồng chính
                ledger.close_stage(None)

    return runner
