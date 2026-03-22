from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

from app.annual_reports.models.annual_report_enums import (
    AnnualReportForm,
    AnnualReportStatus,
    AnnualReportSchedule,
    ClientTypeForReport,
    DeadlineType,
    ExtensionReason,
    SubmissionMethod,
)


class AnnualReportResponse(BaseModel):
    id: int
    business_id: int
    tax_year: int
    client_type: ClientTypeForReport
    form_type: AnnualReportForm
    status: AnnualReportStatus
    deadline_type: DeadlineType
    filing_deadline: Optional[datetime] = None
    custom_deadline_note: Optional[str] = None
    submitted_at: Optional[datetime] = None
    ita_reference: Optional[str] = None
    assessment_amount: Optional[Decimal] = None
    refund_due: Optional[Decimal] = None
    tax_due: Optional[Decimal] = None
    has_rental_income: bool = False
    has_capital_gains: bool = False
    has_foreign_income: bool = False
    has_depreciation: bool = False
    has_exempt_rental: bool = False
    submission_method: Optional[SubmissionMethod] = None
    extension_reason: Optional[ExtensionReason] = None
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
    schedule: AnnualReportSchedule
    is_required: bool
    is_complete: bool
    notes: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    completed_by: Optional[int] = None

    model_config = {"from_attributes": True}


class StatusHistoryResponse(BaseModel):
    id: int
    annual_report_id: int
    from_status: Optional[AnnualReportStatus] = None
    to_status: AnnualReportStatus
    changed_by: int
    note: Optional[str] = None
    occurred_at: datetime

    model_config = {"from_attributes": True}


class AnnualReportDetailResponse(AnnualReportResponse):
    schedules: list[ScheduleEntryResponse] = []
    status_history: list[StatusHistoryResponse] = []
    # פרטי מס — מ-AnnualReportDetail
    pension_contribution: Optional[Decimal] = None
    donation_amount: Optional[Decimal] = None
    other_credits: Optional[Decimal] = None
    client_approved_at: Optional[datetime] = None
    internal_notes: Optional[str] = None
    amendment_reason: Optional[str] = None
    # שדות מ-AnnualReport (מס מחושב)
    tax_refund_amount: Optional[float] = None
    tax_due_amount: Optional[float] = None
    # סיכום פיננסי — מחושב בשירות
    total_income: Optional[Decimal] = None
    total_expenses: Optional[Decimal] = None
    taxable_income: Optional[Decimal] = None
    profit: Optional[Decimal] = None
    final_balance: Optional[Decimal] = None


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
    amended: int = 0
    completion_rate: float
    overdue_count: int