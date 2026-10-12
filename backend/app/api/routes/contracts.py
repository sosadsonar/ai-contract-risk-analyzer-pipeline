from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile
)
from sqlalchemy.orm import Session

from app.core.database import get_db
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
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are currently supported"
        )

    contents = await file.read()

    try:
        contract, text_length = process_uploaded_contract(
            db=db,
            filename=file.filename,
            file_bytes=contents
        )

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