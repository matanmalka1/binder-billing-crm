from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChargeCreateRequest(BaseModel):
    client_id: int
    amount: float = Field(gt=0)
    charge_type: str
    period: Optional[str] = None
    currency: str = "ILS"


class ChargeResponse(BaseModel):
    id: int
    client_id: int
    amount: float
    currency: str
    charge_type: str
    period: Optional[str] = None
    status: str
    created_at: datetime
    issued_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ChargeListResponse(BaseModel):
    items: list[ChargeResponse]
    page: int
    page_size: int
    total: int