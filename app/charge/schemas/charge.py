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
    client_name: Optional[str] = None
    amount: float
    currency: str
    charge_type: str
    period: Optional[str] = None
    status: str
    created_at: datetime
    issued_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    created_by: Optional[int] = None
    issued_by: Optional[int] = None
    paid_by: Optional[int] = None
    canceled_by: Optional[int] = None
    canceled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None

    model_config = {"from_attributes": True}


class ChargeResponseSecretary(BaseModel):
    """Charge response for secretary (no financial data)."""

    id: int
    client_id: int
    client_name: Optional[str] = None
    charge_type: str
    period: Optional[str] = None
    status: str
    created_at: datetime
    issued_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ChargeCancelRequest(BaseModel):
    reason: Optional[str] = None


class ChargeListResponse(BaseModel):
    items: list[ChargeResponse | ChargeResponseSecretary]
    page: int
    page_size: int
    total: int
