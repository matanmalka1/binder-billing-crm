from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

from app.core.api_types import ApiDecimal


class VatSummaryCard(BaseModel):
    net_vat_total: ApiDecimal
    periods_filed: int
    periods_total: int
    latest_period: Optional[str] = None


class AnnualReportCard(BaseModel):
    status: Optional[str] = None
    form_type: Optional[str] = None
    filing_deadline: Optional[str] = None
    refund_due: Optional[ApiDecimal] = None
    tax_due: Optional[ApiDecimal] = None


class ChargesCard(BaseModel):
    total_outstanding: ApiDecimal
    unpaid_count: int


class AdvancePaymentsCard(BaseModel):
    total_paid: ApiDecimal
    count: int


class BindersCard(BaseModel):
    active_count: int
    in_office_count: int


class DocumentsCard(BaseModel):
    total_count: int
    present_count: int


class BusinessStatusCardResponse(BaseModel):
    client_id: int
    business_id: int
    year: int
    client_vat: VatSummaryCard  # shared across all businesses of this client
    annual_report: AnnualReportCard
    charges: ChargesCard
    advance_payments: AdvancePaymentsCard
    binders: BindersCard
    documents: DocumentsCard
