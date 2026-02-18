from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class AdvancePaymentRow(BaseModel):
    id: int
    client_id: int
    tax_deadline_id: Optional[int] = None
    month: int
    year: int
    expected_amount: Optional[float] = None
    paid_amount: Optional[float] = None
    status: str
    due_date: date
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AdvancePaymentListResponse(BaseModel):
    items: list[AdvancePaymentRow]
    page: int
    page_size: int
    total: int


class AdvancePaymentUpdateRequest(BaseModel):
    paid_amount: Optional[float] = None
    status: Optional[str] = None
