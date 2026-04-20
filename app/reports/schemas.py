from datetime import date
from typing import Optional

from pydantic import BaseModel

from app.annual_reports.models.annual_report_enums import AnnualReportForm, AnnualReportStatus


class VatComplianceReportItemResponse(BaseModel):
    client_record_id: int
    client_name: str
    periods_expected: int
    periods_filed: int
    periods_open: int
    on_time_count: int
    late_count: int
    compliance_rate: float


class VatComplianceStalePendingResponse(BaseModel):
    client_record_id: int
    client_name: str
    period: str
    days_pending: int


class VatComplianceReportResponse(BaseModel):
    year: int
    total_clients: int
    items: list[VatComplianceReportItemResponse]
    stale_pending: list[VatComplianceStalePendingResponse]


class AdvancePaymentReportItemResponse(BaseModel):
    client_record_id: int
    client_name: str
    total_expected: float
    total_paid: float
    overdue_count: int
    gap: float


class AdvancePaymentCollectionsReportResponse(BaseModel):
    year: int
    month: Optional[int] = None
    total_expected: float
    total_paid: float
    collection_rate: float
    total_gap: float
    items: list[AdvancePaymentReportItemResponse]


class AnnualReportStatusClientResponse(BaseModel):
    client_record_id: int
    client_name: str
    form_type: Optional[AnnualReportForm] = None
    filing_deadline: Optional[date] = None
    days_until_deadline: Optional[int] = None


class AnnualReportStatusGroupResponse(BaseModel):
    status: AnnualReportStatus
    count: int
    clients: list[AnnualReportStatusClientResponse]


class AnnualReportStatusReportResponse(BaseModel):
    tax_year: int
    total: int
    statuses: list[AnnualReportStatusGroupResponse]


class AgingReportItemResponse(BaseModel):
    client_record_id: int
    client_name: str
    total_outstanding: float
    current: float
    days_30: float
    days_60: float
    days_90_plus: float
    oldest_invoice_date: Optional[date] = None
    oldest_invoice_days: Optional[int] = None


class AgingReportSummaryResponse(BaseModel):
    total_clients: int
    total_current: float
    total_30_days: float
    total_60_days: float
    total_90_plus: float


class AgingReportResponse(BaseModel):
    report_date: date
    total_outstanding: float
    items: list[AgingReportItemResponse]
    summary: AgingReportSummaryResponse
    capped: bool
    cap_limit: int
