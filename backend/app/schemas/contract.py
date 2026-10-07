from datetime import datetime
from pydantic import BaseModel


class ContractResponse(BaseModel):
    id: int
    filename: str
    status: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }