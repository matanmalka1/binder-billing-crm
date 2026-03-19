from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class AnnualReportCreateRequest(BaseModel):
    business_id: int
    tax_year: int
    client_type: str
    deadline_type: str = "standard"
    assigned_to: Optional[int] = None
    notes: Optional[str] = None
    has_rental_income: bool = False
    has_capital_gains: bool = False
    has_foreign_income: bool = False
    has_depreciation: bool = False
    has_exempt_rental: bool = False


class AmendRequest(BaseModel):
    reason: str


class StatusTransitionRequest(BaseModel):
    status: str
    note: Optional[str] = None
    ita_reference: Optional[str] = None
    assessment_amount: Optional[Decimal] = None
    refund_due: Optional[Decimal] = None
    tax_due: Optional[Decimal] = None


class DeadlineUpdateRequest(BaseModel):
    deadline_type: str
    custom_deadline_note: Optional[str] = None


class SubmitRequest(BaseModel):
    submitted_at: Optional[datetime] = None
    ita_reference: Optional[str] = None
    note: Optional[str] = None


class StageTransitionRequest(BaseModel):
    to_stage: str


class ScheduleAddRequest(BaseModel):
    schedule: str
    notes: Optional[str] = None


class ScheduleCompleteRequest(BaseModel):
    schedule: str
