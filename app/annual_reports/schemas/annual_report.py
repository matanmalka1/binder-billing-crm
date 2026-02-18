from datetime import date, datetime
from typing import Optional
from decimal import Decimal

from pydantic import BaseModel


# ── Create ──────────────────────────────────────────────────────────────────

class AnnualReportCreateRequest(BaseModel):
    client_id: int
    tax_year: int
    client_type: str                          # ClientTypeForReport value
    deadline_type: str = "standard"           # DeadlineType value
    assigned_to: Optional[int] = None
    notes: Optional[str] = None
    has_rental_income: bool = False
    has_capital_gains: bool = False
    has_foreign_income: bool = False
    has_depreciation: bool = False
    has_exempt_rental: bool = False


# ── Core response ────────────────────────────────────────────────────────────

class AnnualReportResponse(BaseModel):
    id: int
    client_id: int
    tax_year: int
    client_type: str
    form_type: str
    status: str
    deadline_type: str
    filing_deadline: Optional[datetime] = None
    custom_deadline_note: Optional[str] = None
    submitted_at: Optional[datetime] = None
    ita_reference: Optional[str] = None
    assessment_amount: Optional[float] = None
    refund_due: Optional[float] = None
    tax_due: Optional[float] = None
    has_rental_income: bool = False
    has_capital_gains: bool = False
    has_foreign_income: bool = False
    has_depreciation: bool = False
    has_exempt_rental: bool = False
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    assigned_to: Optional[int] = None
    created_by: int

    model_config = {"from_attributes": True}


class AnnualReportListResponse(BaseModel):
    items: list[AnnualReportResponse]
    page: int
    page_size: int
    total: int


# ── Detail response (with schedules + history) ────────────────────────────────

class ScheduleEntryResponse(BaseModel):
    id: int
    annual_report_id: int
    schedule: str
    is_required: bool
    is_complete: bool
    notes: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class StatusHistoryResponse(BaseModel):
    id: int
    annual_report_id: int
    from_status: Optional[str] = None
    to_status: str
    changed_by: int
    changed_by_name: str
    note: Optional[str] = None
    occurred_at: datetime

    model_config = {"from_attributes": True}


class AnnualReportDetailResponse(AnnualReportResponse):
    schedules: list[ScheduleEntryResponse] = []
    status_history: list[StatusHistoryResponse] = []

    # Detail sub-object fields (from AnnualReportDetail entity)
    tax_refund_amount: Optional[float] = None
    tax_due_amount: Optional[float] = None
    client_approved_at: Optional[datetime] = None
    internal_notes: Optional[str] = None


# ── Status transition ────────────────────────────────────────────────────────

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


# ── Kanban stage transition (UI helper) ─────────────────────────────────────

class StageTransitionRequest(BaseModel):
    to_stage: str


# ── Schedule actions ─────────────────────────────────────────────────────────

class ScheduleAddRequest(BaseModel):
    schedule: str
    notes: Optional[str] = None


class ScheduleCompleteRequest(BaseModel):
    schedule: str


# ── Season dashboard ─────────────────────────────────────────────────────────

class SeasonSummaryResponse(BaseModel):
    tax_year: int
    total: int
    not_started: int
    collecting_docs: int
    docs_complete: int
    in_preparation: int
    pending_client: int
    submitted: int
    accepted: int
    assessment_issued: int
    objection_filed: int
    closed: int
    completion_rate: float
    overdue_count: int
