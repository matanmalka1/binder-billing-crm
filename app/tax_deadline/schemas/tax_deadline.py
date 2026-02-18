from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class TaxDeadlineCreateRequest(BaseModel):
    client_id: int
    deadline_type: str
    due_date: date
    payment_amount: Optional[float] = None
    description: Optional[str] = None


class TaxDeadlineResponse(BaseModel):
    id: int
    client_id: int
    deadline_type: str
    due_date: date
    status: str
    payment_amount: Optional[float] = None
    currency: str
    description: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TaxDeadlineListResponse(BaseModel):
    items: list[TaxDeadlineResponse]
    page: int
    page_size: int
    total: int


class DeadlineUrgentItem(BaseModel):
    id: int
    client_id: int
    client_name: str
    deadline_type: str
    due_date: date
    urgency: str
    days_remaining: int
    payment_amount: Optional[float] = None


class DashboardDeadlinesResponse(BaseModel):
    urgent: list[DeadlineUrgentItem]
    upcoming: list[TaxDeadlineResponse]