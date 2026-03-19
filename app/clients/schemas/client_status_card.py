from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class VatSummaryCard(BaseModel):
    net_vat_total: Decimal
    periods_filed: int
    periods_total: int
    latest_period: Optional[str] = None


class AnnualReportCard(BaseModel):
    status: Optional[str] = None
    form_type: Optional[str] = None
    filing_deadline: Optional[str] = None
    refund_due: Optional[Decimal] = None
    tax_due: Optional[Decimal] = None


class ChargesCard(BaseModel):
    total_outstanding: Decimal
    unpaid_count: int


class AdvancePaymentsCard(BaseModel):
    total_paid: Decimal
    count: int


class BindersCard(BaseModel):
    active_count: int
    in_office_count: int


class DocumentsCard(BaseModel):
    total_count: int
    present_count: int


class ClientStatusCardResponse(BaseModel):
    client_id: int
    business_id: int
    year: int
    vat: VatSummaryCard
    annual_report: AnnualReportCard
    charges: ChargesCard
    advance_payments: AdvancePaymentsCard
    binders: BindersCard
    documents: DocumentsCard
