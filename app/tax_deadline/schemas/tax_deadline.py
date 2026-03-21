from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.tax_deadline.models.tax_deadline import (
    DeadlineType,
    TaxDeadlineStatus,
    UrgencyLevel,
)


class TaxDeadlineCreateRequest(BaseModel):
    business_id: int
    deadline_type: DeadlineType             # enum
    due_date: date
    period: Optional[str] = None            # "YYYY-MM" — קיים במודל
    payment_amount: Optional[Decimal] = Field(None, ge=0)
    description: Optional[str] = None


class TaxDeadlineResponse(BaseModel):
    id: int
    business_id: int
    business_name: Optional[str] = None     # enriched by service
    deadline_type: DeadlineType
    period: Optional[str] = None
    due_date: date
    status: TaxDeadlineStatus
    payment_amount: Optional[Decimal] = None
    description: Optional[str] = None
    completed_at: Optional[datetime] = None
    completed_by: Optional[int] = None      
    advance_payment_id: Optional[int] = None  
    created_at: datetime
    available_actions: list[dict] = []

    model_config = {"from_attributes": True}


class TaxDeadlineUpdateRequest(BaseModel):
    deadline_type: Optional[DeadlineType] = None
    due_date: Optional[date] = None
    period: Optional[str] = None
    payment_amount: Optional[Decimal] = Field(None, ge=0)
    description: Optional[str] = None


class TaxDeadlineListResponse(BaseModel):
    items: list[TaxDeadlineResponse]
    page: int
    page_size: int
    total: int


class DeadlineUrgentItem(BaseModel):
    id: int
    business_id: int
    business_name: str
    deadline_type: DeadlineType
    due_date: date
    urgency: UrgencyLevel              
    days_remaining: int
    payment_amount: Optional[Decimal] = None


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
    deadline_type: DeadlineType
    period: Optional[str] = None
    due_date: date
    status: TaxDeadlineStatus
    days_remaining: int
    milestone_label: str
    payment_amount: Optional[Decimal] = None