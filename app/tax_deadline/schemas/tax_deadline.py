from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class TaxDeadlineCreateRequest(BaseModel):
    business_id: int
    deadline_type: str
    due_date: date
    payment_amount: Optional[float] = None
    description: Optional[str] = None


class TaxDeadlineResponse(BaseModel):
    id: int
    business_id: int
    client_name: Optional[str] = None
    deadline_type: str
    due_date: date
    status: str
    payment_amount: Optional[float] = None
    currency: str
    description: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    available_actions: list[dict] = []

    model_config = {"from_attributes": True}


class TaxDeadlineUpdateRequest(BaseModel):
    deadline_type: Optional[str] = None
    due_date: Optional[date] = None
    payment_amount: Optional[float] = None
    description: Optional[str] = None


class TaxDeadlineListResponse(BaseModel):
    items: list[TaxDeadlineResponse]
    page: int
    page_size: int
    total: int


class DeadlineUrgentItem(BaseModel):
    id: int
    business_id: int
    client_name: str
    deadline_type: str
    due_date: date
    urgency: str
    days_remaining: int
    payment_amount: Optional[float] = None


class DashboardDeadlinesResponse(BaseModel):
    urgent: list[DeadlineUrgentItem]
    upcoming: list[TaxDeadlineResponse]


class GenerateDeadlinesRequest(BaseModel):
    business_id: int
    year: int


class GenerateDeadlinesResponse(BaseModel):
    created_count: int


class TimelineEntry(BaseModel):
    id: int
    business_id: int
    deadline_type: str
    due_date: date
    status: str
    days_remaining: int
    milestone_label: str
    payment_amount: Optional[float] = None
