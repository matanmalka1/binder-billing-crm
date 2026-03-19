from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ChargeCreateRequest(BaseModel):
    business_id: int
    amount: float = Field(gt=0)
    charge_type: str
    period: Optional[str] = None
    currency: str = "ILS"


class ChargeResponse(BaseModel):
    id: int
    business_id: int
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
    business_id: int
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


class BulkChargeActionRequest(BaseModel):
    charge_ids: list[int] = Field(min_length=1)
    action: Literal["issue", "mark-paid", "cancel"]
    cancellation_reason: Optional[str] = None


class BulkChargeFailedItem(BaseModel):
    id: int
    error: str


class BulkChargeActionResponse(BaseModel):
    succeeded: list[int]
    failed: list[BulkChargeFailedItem]
