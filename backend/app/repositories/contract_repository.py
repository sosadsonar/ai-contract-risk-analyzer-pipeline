from sqlalchemy.orm import Session
from sqlalchemy import select, func, text

from app.models.contract import Contract
from app.core.config import settings
from app.core.upload_limits import UploadCapacityError


def create_contract(
    db: Session,
    filename: str,
    original_text: str
) -> Contract:
    if '\x00' in original_text:
        raise ValueError('PDF text contains unsupported NUL characters')
    if len(original_text) > settings.pdf_max_text_chars:
        raise ValueError('PDF exceeds extracted text limit')
    try:
        dialect = db.get_bind().dialect.name
        if dialect == 'postgresql':
            db.execute(text("SET LOCAL statement_timeout = '3000ms'"))
            if not db.scalar(text('SELECT pg_try_advisory_xact_lock(1129464146, 1)')):
                raise UploadCapacityError('Contract storage is busy')
        elif dialect == 'sqlite':
            db.execute(text('BEGIN IMMEDIATE'))
        else:
            raise UploadCapacityError('Storage quota locking unsupported for this database')
        count, characters = db.execute(select(func.count(Contract.id),
            func.coalesce(func.sum(func.length(Contract.original_text)), 0))).one()
        if (count >= settings.pdf_max_stored_contracts
                or characters + len(original_text) > settings.pdf_max_stored_text_chars):
            raise UploadCapacityError('Contract storage quota reached')
        return _insert_contract(db, filename, original_text)
    except Exception:
        db.rollback()
        raise


def _insert_contract(db, filename, original_text):
    contract = Contract(
        filename=filename,
        original_text=original_text,
        status="uploaded"
    )

    db.add(contract)
    db.commit()
    db.refresh(contract)

    return contract
