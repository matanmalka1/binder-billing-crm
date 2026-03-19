from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AnnualReportResponse(BaseModel):
    id: int
    business_id: int
    client_id: Optional[int] = None  # תאימות לאחור
    client_name: Optional[str] = None
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
    available_actions: list[dict] = []

    model_config = {"from_attributes": True}


class AnnualReportListResponse(BaseModel):
    items: list[AnnualReportResponse]
    page: int
    page_size: int
    total: int


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
    tax_refund_amount: Optional[float] = None
    tax_due_amount: Optional[float] = None
    client_approved_at: Optional[datetime] = None
    internal_notes: Optional[str] = None
    amendment_reason: Optional[str] = None
    total_income: float = 0.0
    total_expenses: float = 0.0
    taxable_income: float = 0.0
    profit: Optional[float] = None
    final_balance: Optional[float] = None


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