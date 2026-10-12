from sqlalchemy.orm import Session

from app.services.document_service import extract_pdf_text
from app.repositories.contract_repository import create_contract


def process_uploaded_contract(
    db: Session,
    filename: str,
    file_bytes: bytes
):
    text = extract_pdf_text(file_bytes)

    if not text.strip():
        raise ValueError(
            "No extractable text found in PDF"
        )

    contract = create_contract(
        db=db,
        filename=filename,
        original_text=text
    )

    return contract, len(text)