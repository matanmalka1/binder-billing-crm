from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

from app.core.api_types import ApiDateTime, ApiDecimal
from app.annual_reports.models.annual_report_enums import (
    AnnualReportForm,
    AnnualReportStatus,
    AnnualReportSchedule,
    ClientTypeForReport,
    FilingDeadlineType,
    ExtensionReason,
    ReportStage,
    SubmissionMethod,
)


class AnnualReportResponse(BaseModel):
    id: int
    client_id: int
    client_name: Optional[str] = None
    business_name: Optional[str] = None
    tax_year: int
    client_type: ClientTypeForReport
    form_type: AnnualReportForm
    status: AnnualReportStatus
    deadline_type: FilingDeadlineType
    filing_deadline: Optional[ApiDateTime] = None
    custom_deadline_note: Optional[str] = None
    submitted_at: Optional[ApiDateTime] = None
    ita_reference: Optional[str] = None
    assessment_amount: Optional[ApiDecimal] = None
    refund_due: Optional[ApiDecimal] = None
    tax_due: Optional[ApiDecimal] = None
    has_rental_income: bool = False
    has_capital_gains: bool = False
    has_foreign_income: bool = False
    has_depreciation: bool = False
    submission_method: Optional[SubmissionMethod] = None
    extension_reason: Optional[ExtensionReason] = None
    notes: Optional[str] = None
    created_at: ApiDateTime
    updated_at: ApiDateTime
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
    created_at: ApiDateTime
    completed_at: Optional[ApiDateTime] = None
    completed_by: Optional[int] = None

    model_config = {"from_attributes": True}


class StatusHistoryResponse(BaseModel):
    id: int
    annual_report_id: int
    from_status: Optional[AnnualReportStatus] = None
    to_status: AnnualReportStatus
    changed_by: int
    changed_by_name: Optional[str] = None
    note: Optional[str] = None
    occurred_at: ApiDateTime

    model_config = {"from_attributes": True}


class AnnualReportDetailResponse(AnnualReportResponse):
    schedules: list[ScheduleEntryResponse] = []
    status_history: list[StatusHistoryResponse] = []
    # פרטי מס — מ-AnnualReportDetail
    pension_contribution: Optional[ApiDecimal] = None
    donation_amount: Optional[ApiDecimal] = None
    other_credits: Optional[ApiDecimal] = None
    # נקודות זיכוי — מ-AnnualReportDetail
    credit_points: Optional[ApiDecimal] = None
    pension_credit_points: Optional[ApiDecimal] = None
    life_insurance_credit_points: Optional[ApiDecimal] = None
    tuition_credit_points: Optional[ApiDecimal] = None
    client_approved_at: Optional[ApiDateTime] = None
    internal_notes: Optional[str] = None
    amendment_reason: Optional[str] = None
    # שדות מ-AnnualReport (מס מחושב)
    tax_refund_amount: Optional[float] = None
    tax_due_amount: Optional[float] = None
    # סיכום פיננסי — מחושב בשירות
    total_income: Optional[ApiDecimal] = None
    total_expenses: Optional[ApiDecimal] = None
    taxable_income: Optional[ApiDecimal] = None
    profit: Optional[ApiDecimal] = None
    final_balance: Optional[ApiDecimal] = None


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


class AnnualReportKanbanItemResponse(BaseModel):
    id: int
    client_id: int
    client_name: Optional[str] = None
    business_name: Optional[str] = None
    tax_year: int
    days_until_due: Optional[int] = None


class AnnualReportKanbanStageResponse(BaseModel):
    stage: ReportStage
    reports: list[AnnualReportKanbanItemResponse]


class AnnualReportKanbanViewResponse(BaseModel):
    stages: list[AnnualReportKanbanStageResponse]
