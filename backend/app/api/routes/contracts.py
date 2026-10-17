from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile
)
from sqlalchemy.orm import Session
import asyncio
from starlette.concurrency import run_in_threadpool

from app.core.database import get_db
from app.core.config import settings
from app.core.upload_limits import UploadCapacityError
from app.services.contract_service import process_uploaded_contract


router = APIRouter(
    prefix="/api/v1/contracts",
    tags=["contracts"]
)


@router.post("/upload")
async def upload_contract(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are currently supported"
        )

    contents = await file.read(settings.pdf_max_bytes + 1)
    if len(contents) > settings.pdf_max_bytes:
        raise HTTPException(413, 'PDF exceeds upload byte limit')
    if len(file.filename) > 255:
        raise HTTPException(400, 'PDF filename exceeds 255 characters')

    try:
        task = asyncio.create_task(run_in_threadpool(process_uploaded_contract,
            db=db,
            filename=file.filename,
            file_bytes=contents
        ))
        # Keep capacity and the DB session until underlying work actually ends.
        cancelled = False
        while True:
            try:
                contract, text_length = await asyncio.shield(task)
                break
            except asyncio.CancelledError:
                cancelled = True
                if task.done():
                    raise
        if cancelled:
            raise asyncio.CancelledError

    except UploadCapacityError as error:
        raise HTTPException(503, str(error), headers={'Retry-After':'60'}) from None

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error)
        )

    return {
        "id": contract.id,
        "filename": contract.filename,
        "status": contract.status,
        "text_length": text_length
    }
