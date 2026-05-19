
from pydantic import BaseModel

from app.annual_reports.models.annual_report_enums import (
    AnnualReportSchedule,
    AnnualReportStatus,
    ClientAnnualFilingType,
    ExtensionReason,
    FilingDeadlineType,
    ReportStage,
    SubmissionMethod,
)
from app.core.api_types import ApiDateTime, ApiDecimal


class AnnualReportCreateRequest(BaseModel):
    client_record_id: int
    tax_year: int
    client_type: ClientAnnualFilingType
    deadline_type: FilingDeadlineType = FilingDeadlineType.STANDARD
    assigned_to: int | None = None
    notes: str | None = None
    submission_method: SubmissionMethod | None = None
    extension_reason: ExtensionReason | None = None
    has_rental_income: bool = False
    has_capital_gains: bool = False
    has_foreign_income: bool = False
    has_depreciation: bool = False


class AmendRequest(BaseModel):
    reason: str


class StatusTransitionRequest(BaseModel):
    status: AnnualReportStatus  # enum — לא str חופשי
    note: str | None = None
    ita_reference: str | None = None
    assessment_amount: ApiDecimal | None = None
    refund_due: ApiDecimal | None = None
    tax_due: ApiDecimal | None = None


class DeadlineUpdateRequest(BaseModel):
    deadline_type: FilingDeadlineType  # enum
    custom_deadline_note: str | None = None


class SubmitRequest(BaseModel):
    submitted_at: ApiDateTime | None = None
    ita_reference: str | None = None
    submission_method: SubmissionMethod | None = None
    note: str | None = None


class StageTransitionRequest(BaseModel):
    to_stage: ReportStage  # enum


class ScheduleAddRequest(BaseModel):
    schedule: AnnualReportSchedule  # enum
    notes: str | None = None


class ScheduleCompleteRequest(BaseModel):
    schedule: AnnualReportSchedule  # enum
