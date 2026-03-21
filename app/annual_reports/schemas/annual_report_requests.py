from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

from app.annual_reports.models.annual_report_enums import (
    ClientTypeForReport,
    DeadlineType,
    AnnualReportStatus,
    AnnualReportSchedule,
    ExtensionReason,
    SubmissionMethod,
    ReportStage,
)


class AnnualReportCreateRequest(BaseModel):
    business_id: int
    tax_year: int
    client_type: ClientTypeForReport        # enum — לא str חופשי
    deadline_type: DeadlineType = DeadlineType.STANDARD
    assigned_to: Optional[int] = None
    notes: Optional[str] = None
    submission_method: Optional[SubmissionMethod] = None
    extension_reason: Optional[ExtensionReason] = None
    has_rental_income: bool = False
    has_capital_gains: bool = False
    has_foreign_income: bool = False
    has_depreciation: bool = False
    has_exempt_rental: bool = False


class AmendRequest(BaseModel):
    reason: str


class StatusTransitionRequest(BaseModel):
    status: AnnualReportStatus              # enum — לא str חופשי
    note: Optional[str] = None
    ita_reference: Optional[str] = None
    assessment_amount: Optional[Decimal] = None
    refund_due: Optional[Decimal] = None
    tax_due: Optional[Decimal] = None


class DeadlineUpdateRequest(BaseModel):
    deadline_type: DeadlineType             # enum
    custom_deadline_note: Optional[str] = None


class SubmitRequest(BaseModel):
    submitted_at: Optional[datetime] = None
    ita_reference: Optional[str] = None
    submission_method: Optional[SubmissionMethod] = None
    note: Optional[str] = None


class StageTransitionRequest(BaseModel):
    to_stage: ReportStage                   # enum


class ScheduleAddRequest(BaseModel):
    schedule: AnnualReportSchedule          # enum
    notes: Optional[str] = None


class ScheduleCompleteRequest(BaseModel):
    schedule: AnnualReportSchedule          # enum