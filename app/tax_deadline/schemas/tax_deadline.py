from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.core.api_types import ApiDateTime, ApiDecimal
from app.tax_deadline.models.tax_deadline import (
    DeadlineType,
    TaxDeadlineStatus,
    UrgencyLevel,
)

class TaxDeadlineCreateRequest(BaseModel):
    client_id: int
    deadline_type: DeadlineType             # enum
    due_date: date
    period: Optional[str] = None            # "YYYY-MM" — קיים במודל
    payment_amount: Optional[ApiDecimal] = Field(None, ge=0)
    description: Optional[str] = None

    @field_validator("period")
    @classmethod
    def validate_period(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if len(value) != 7 or value[4] != "-" or not value[:4].isdigit() or not value[5:7].isdigit():
            raise ValueError("period must be in YYYY-MM format")
        month = int(value[5:7])
        if month < 1 or month > 12:
            raise ValueError("period must be in YYYY-MM format")
        return value

class TaxDeadlineResponse(BaseModel):
    id: int
    client_id: int
    business_name: Optional[str] = None     # enriched by service (client full_name)
    deadline_type: DeadlineType
    period: Optional[str] = None
    due_date: date
    status: TaxDeadlineStatus
    payment_amount: Optional[ApiDecimal] = None
    description: Optional[str] = None
    completed_at: Optional[ApiDateTime] = None
    completed_by: Optional[int] = None
    advance_payment_id: Optional[int] = None
    created_at: ApiDateTime
    available_actions: list[dict] = []

    model_config = {"from_attributes": True}

class TaxDeadlineUpdateRequest(BaseModel):
    deadline_type: Optional[DeadlineType] = None
    due_date: Optional[date] = None
    period: Optional[str] = None
    payment_amount: Optional[ApiDecimal] = Field(None, ge=0)
    description: Optional[str] = None

    @field_validator("period")
    @classmethod
    def validate_period(cls, value: Optional[str]) -> Optional[str]:
        return TaxDeadlineCreateRequest.validate_period(value)

class TaxDeadlineListResponse(BaseModel):
    items: list[TaxDeadlineResponse]
    page: int
    page_size: int
    total: int

class DeadlineUrgentItem(BaseModel):
    id: int
    client_id: int
    business_name: str
    deadline_type: DeadlineType
    due_date: date
    urgency: UrgencyLevel
    days_remaining: int
    payment_amount: Optional[ApiDecimal] = None

class DashboardDeadlinesResponse(BaseModel):
    urgent: list[DeadlineUrgentItem]
    upcoming: list[TaxDeadlineResponse]

class GenerateDeadlinesRequest(BaseModel):
    client_id: int
    year: int

class GenerateDeadlinesResponse(BaseModel):
    created_count: int

class TimelineEntry(BaseModel):
    id: int
    client_id: int
    deadline_type: DeadlineType
    period: Optional[str] = None
    due_date: date
    status: TaxDeadlineStatus
    days_remaining: int
    milestone_label: str
    payment_amount: Optional[ApiDecimal] = None
