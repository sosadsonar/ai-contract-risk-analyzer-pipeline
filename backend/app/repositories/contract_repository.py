from sqlalchemy.orm import Session

from app.models.contract import Contract


def create_contract(
    db: Session,
    filename: str,
    original_text: str
) -> Contract:

    contract = Contract(
        filename=filename,
        original_text=original_text,
        status="uploaded"
    )

    db.add(contract)
    db.commit()
    db.refresh(contract)

    return contract