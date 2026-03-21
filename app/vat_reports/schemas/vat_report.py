"""Pydantic request / response schemas for the VAT Reports module."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
import re

from pydantic import BaseModel, field_validator, model_validator

from app.vat_reports.models.vat_enums import (
    CounterpartyIdType,
    DocumentType,
    ExpenseCategory,
    InvoiceType,
    VatRateType,
    VatWorkItemStatus,
)
from app.businesses.models.business import BusinessStatus
from app.businesses.models.business_tax_profile import VatType
from app.annual_reports.models.annual_report_enums import SubmissionMethod


# ── Work Item ─────────────────────────────────────────────────────────────────

class VatWorkItemCreateRequest(BaseModel):
    business_id: int
    period: str                             # "YYYY-MM"
    assigned_to: Optional[int] = None
    mark_pending: bool = False
    pending_materials_note: Optional[str] = None

    @field_validator("period")
    @classmethod
    def validate_period(cls, v: str) -> str:
        if not re.fullmatch(r"\d{4}-(?:0[1-9]|1[0-2])", v):
            raise ValueError("התקופה חייבת להיות בפורמט YYYY-MM")
        return v


class VatWorkItemResponse(BaseModel):
    id: int
    business_id: int
    business_name: Optional[str] = None    # enriched by service
    business_status: Optional[BusinessStatus] = None  # enum
    period: str
    period_type: VatType                   # קיים במודל — snapshot של סוג הדיווח
    status: VatWorkItemStatus
    pending_materials_note: Optional[str] = None
    total_output_vat: Decimal
    total_input_vat: Decimal
    net_vat: Decimal
    total_output_net: Decimal              # קיים במודל — שדה 87
    total_input_net: Decimal               # קיים במודל — שדה 66
    final_vat_amount: Optional[Decimal] = None
    is_overridden: bool
    override_justification: Optional[str] = None
    submission_method: Optional[SubmissionMethod] = None  # שם חדש במודל
    filed_at: Optional[datetime] = None
    filed_by: Optional[int] = None
    filed_by_name: Optional[str] = None
    submission_reference: Optional[str] = None
    is_amendment: bool = False
    amends_item_id: Optional[int] = None
    created_by: int
    assigned_to: Optional[int] = None
    assigned_to_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    # Derived — not stored
    submission_deadline: Optional[date] = None
    days_until_deadline: Optional[int] = None
    is_overdue: Optional[bool] = None

    model_config = {"from_attributes": True}


class VatWorkItemListResponse(BaseModel):
    items: list[VatWorkItemResponse]
    total: int


# ── Materials ─────────────────────────────────────────────────────────────────

class MarkMaterialsCompleteRequest(BaseModel):
    pass


# ── Invoices ──────────────────────────────────────────────────────────────────

class VatInvoiceCreateRequest(BaseModel):
    invoice_type: InvoiceType
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None    # Date — לא DateTime
    counterparty_name: Optional[str] = None
    net_amount: Decimal
    vat_amount: Decimal
    counterparty_id: Optional[str] = None
    counterparty_id_type: Optional[CounterpartyIdType] = None  # קיים במודל
    expense_category: Optional[ExpenseCategory] = None
    rate_type: VatRateType = VatRateType.STANDARD
    document_type: Optional[DocumentType] = None

    @field_validator("net_amount")
    @classmethod
    def net_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("הסכום נטו חייב להיות חיובי")
        return v

    @field_validator("vat_amount")
    @classmethod
    def vat_non_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("הסכום של המע\"מ לא יכול להיות שלילי")
        return v

    @model_validator(mode="after")
    def validate_counterparty_id(self) -> "VatInvoiceCreateRequest":
        cid = self.counterparty_id
        cid_type = self.counterparty_id_type
        if cid is None:
            return self
        if cid_type in (CounterpartyIdType.IL_BUSINESS, CounterpartyIdType.IL_PERSONAL):
            if not cid.isdigit() or len(cid) != 9:
                raise ValueError("מספר עוסק / ת\"ז ישראלי חייב להיות 9 ספרות")
        return self


class VatInvoiceResponse(BaseModel):
    id: int
    work_item_id: int
    invoice_type: InvoiceType
    document_type: Optional[DocumentType] = None
    invoice_number: str
    invoice_date: date                     # Date — לא DateTime
    counterparty_name: str
    counterparty_id: Optional[str] = None
    counterparty_id_type: Optional[CounterpartyIdType] = None  # קיים במודל
    net_amount: Decimal
    vat_amount: Decimal
    expense_category: Optional[ExpenseCategory] = None
    rate_type: VatRateType
    deduction_rate: Decimal
    is_exceptional: bool
    created_by: int
    created_at: date                       # Date במודל

    model_config = {"from_attributes": True}


class VatInvoiceListResponse(BaseModel):
    items: list[VatInvoiceResponse]


# ── Status transitions ────────────────────────────────────────────────────────

class SendBackForCorrectionRequest(BaseModel):
    correction_note: str


# ── Filing ────────────────────────────────────────────────────────────────────

class FileVatReturnRequest(BaseModel):
    submission_method: SubmissionMethod    # שם חדש — תואם המודל
    override_amount: Optional[Decimal] = None
    override_justification: Optional[str] = None
    submission_reference: Optional[str] = None
    is_amendment: bool = False
    amends_item_id: Optional[int] = None