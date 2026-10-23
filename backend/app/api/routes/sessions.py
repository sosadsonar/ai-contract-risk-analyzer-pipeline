"""Dev-only sample HTTP contract; replaced entirely by the real pipeline in C-05/C-06."""

import asyncio
import io
import json
from pathlib import Path
from uuid import UUID

from docx import Document
from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, Response

from app.api.errors import api_error
from app.core.enums import Role, SessionStatus
from app.session.mock import MockSession, MockStore

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])
_FIXTURE = Path(__file__).resolve().parents[4] / "tests/fixtures/mock_final_result_v1.json"


def store(request: Request) -> MockStore:
    result: MockStore = request.app.state.mock_store
    result.cleanup()
    return result


def lookup(state: MockStore, raw_id: str) -> MockSession | JSONResponse:
    try:
        sid = UUID(raw_id)
        if sid.version != 4 or str(sid) != raw_id.lower():
            raise ValueError("Invalid UUIDv4")
    except ValueError:
        return api_error(404, "SESSION_NOT_FOUND")
    session = state.sessions.get(sid)
    if session is None:
        return api_error(410 if sid in state.tombstones else 404,
                         "SESSION_EXPIRED" if sid in state.tombstones else "SESSION_NOT_FOUND")
    return session


def ready(session: MockSession) -> JSONResponse | None:
    if session.status == SessionStatus.COMPLETED:
        return None
    if session.status == SessionStatus.REJECTED:
        return api_error(409, "SESSION_REJECTED", details={"error_code": session.error_code})
    return api_error(409, "SESSION_NOT_READY")


def sample(session: MockSession) -> dict:
    with _FIXTURE.open(encoding="utf-8") as fixture:
        result = json.load(fixture)
    result["session_id"] = str(session.session_id)
    result["role"] = session.role.value
    result["analysis_date"] = session.created_at.date().isoformat()
    return result


@router.post("", status_code=201)
async def create(request: Request, role: str | None = Form(default=None),
                 file: UploadFile | None = File(default=None)):
    try:
        parsed_role = Role(role)
    except ValueError:
        return api_error(400, "ROLE_REQUIRED")
    state = store(request)
    error_code = None
    if file is None:
        error_code = "UNSUPPORTED_FILE_TYPE"
    else:
        try:
            data = await file.read(state.settings.MAX_UPLOAD_MB * 1024 * 1024 + 1)
            if len(data) > state.settings.MAX_UPLOAD_MB * 1024 * 1024:
                error_code = "FILE_TOO_LARGE"
            elif not file.filename or not (
                (file.filename.lower().endswith(".pdf") and data.startswith(b"%PDF-"))
                or (file.filename.lower().endswith(".docx") and data.startswith(b"PK\x03\x04"))
            ):
                error_code = "UNSUPPORTED_FILE_TYPE"
        finally:
            await file.close()
    session = state.create(parsed_role, error_code)
    return JSONResponse(status_code=201, content={
        "session_id": str(session.session_id), "status": session.status.value,
        "created_at": session.created_at.isoformat().replace("+00:00", "Z"),
    })


@router.get("/{session_id}/status")
def status(request: Request, session_id: str):
    session = lookup(store(request), session_id)
    if isinstance(session, JSONResponse):
        if session.status_code == 410:
            return {"session_id": session_id, "status": "EXPIRED", "stage": None,
                    "manual_retry_count": 0, "progress": {"completed_units": 0, "total_units": 0},
                    "error_code": None, "updated_at": request.app.state.mock_store.tombstones[UUID(session_id)].isoformat()}
        return session
    completed = {SessionStatus.UPLOADED: 0, SessionStatus.VALIDATING: 1,
                 SessionStatus.PROCESSING: 2, SessionStatus.COMPLETED: 3}.get(session.status, 0)
    return {"session_id": session_id, "status": session.status.value,
            "stage": session.stage.value, "manual_retry_count": session.manual_retry_count,
            "progress": {"completed_units": completed, "total_units": 3},
            "error_code": session.error_code, "updated_at": session.updated_at.isoformat()}


@router.get("/{session_id}/result")
def result(request: Request, session_id: str):
    session = lookup(store(request), session_id)
    if isinstance(session, JSONResponse):
        return session
    session.touch()
    if error := ready(session):
        return error
    return sample(session)


@router.post("/{session_id}/retry")
async def retry(request: Request, session_id: str):
    state = store(request)
    session = lookup(state, session_id)
    if isinstance(session, JSONResponse):
        return session
    session.touch()
    if session.status != SessionStatus.FAILED:
        return api_error(409, "INVALID_SESSION_STATE", details={"status": session.status.value})
    if session.manual_retry_count >= 2:
        return api_error(409, "RETRY_LIMIT_EXCEEDED")
    session.manual_retry_count += 1
    session.status = SessionStatus.UPLOADED
    session.error_code = None
    session.updated_at = session.last_activity_at
    session.task = asyncio.create_task(state.advance(session, None))
    return {"session_id": session_id, "status": session.status.value,
            "manual_retry_count": session.manual_retry_count}


@router.get("/{session_id}/export")
def export(request: Request, session_id: str, format: str = "docx"):
    session = lookup(store(request), session_id)
    if isinstance(session, JSONResponse):
        return session
    session.touch()
    if error := ready(session):
        return error
    if format != "docx":
        return api_error(501, "FEATURE_NOT_ENABLED")
    result = sample(session)
    report = Document()
    report.add_heading("Phân tích rủi ro hợp đồng lao động", 0)
    for clause in result["clauses"]:
        report.add_heading(clause["clause_id"], level=1)
        report.add_paragraph(clause["original_text"])
        for risk in result["risks"]:
            if risk["clause_id"] == clause["clause_id"]:
                report.add_paragraph(f"Rủi ro: {', '.join(risk['risk_labels'])} ({risk['severity']})")
                report.add_paragraph(risk["explanation"])
                report.add_paragraph(f"Căn cứ: {', '.join(risk['citation_ids'])}")
    for citation in result["citations"]:
        report.add_paragraph(f"{citation['citation_id']}: {citation['content']}")
    report.add_paragraph(result["disclaimer"])
    report.add_paragraph(result["data_notice"])
    buffer = io.BytesIO()
    report.save(buffer)
    return Response(buffer.getvalue(), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": 'attachment; filename="report.docx"'})


@router.delete("/{session_id}")
def end(request: Request, session_id: str):
    state = store(request)
    session = lookup(state, session_id)
    if isinstance(session, JSONResponse) and session.status_code != 410:
        return session
    if not isinstance(session, JSONResponse):
        session.touch()
        state.end(session.session_id)
    return {"session_id": session_id, "status": "EXPIRED",
            "message": "Phiên đã kết thúc và dữ liệu phiên đã được xóa."}
