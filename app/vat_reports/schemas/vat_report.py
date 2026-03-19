"""Pydantic request / response schemas for the VAT Reports module."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, field_validator

from app.vat_reports.models.vat_enums import (
    DocumentType,
    ExpenseCategory,
    FilingMethod,
    InvoiceType,
    VatRateType,
    VatWorkItemStatus,
)


# ── Work Item ────────────────────────────────────────────────────────────────

class VatWorkItemCreateRequest(BaseModel):
    business_id: int
    period: str                        # "YYYY-MM"
    assigned_to: Optional[int] = None
    mark_pending: bool = False
    pending_materials_note: Optional[str] = None

    @field_validator("period")
    @classmethod
    def validate_period(cls, v: str) -> str:
        import re
        if not re.fullmatch(r"\d{4}-(?:0[1-9]|1[0-2])", v):
            raise ValueError("התקופה חייבת להיות בפורמט YYYY-MM (למשל '2026-01')")
        return v


class VatWorkItemResponse(BaseModel):
    id: int
    business_id: int
    business_name: Optional[str] = None
    period: str
    status: VatWorkItemStatus
    pending_materials_note: Optional[str]
    total_output_vat: Decimal
    total_input_vat: Decimal
    net_vat: Decimal
    final_vat_amount: Optional[Decimal]
    is_overridden: bool
    override_justification: Optional[str]
    filing_method: Optional[FilingMethod]
    filed_at: Optional[datetime]
    filed_by: Optional[int]
    filed_by_name: Optional[str] = None
    created_by: int
    assigned_to: Optional[int]
    assigned_to_name: Optional[str] = None
    business_status: Optional[str] = None  # "active" | "frozen" | "closed"
    created_at: datetime
    updated_at: datetime
    submission_reference: Optional[str] = None
    is_amendment: bool = False
    amends_item_id: Optional[int] = None
    # Derived — not stored
    submission_deadline: Optional[date] = None
    days_until_deadline: Optional[int] = None
    is_overdue: Optional[bool] = None

    model_config = {"from_attributes": True}


class VatWorkItemListResponse(BaseModel):
    items: list[VatWorkItemResponse]
    total: int


# ── Materials ────────────────────────────────────────────────────────────────

class MarkMaterialsCompleteRequest(BaseModel):
    pass  # No body required — actor inferred from JWT


# ── Invoices ─────────────────────────────────────────────────────────────────

class VatInvoiceCreateRequest(BaseModel):
    invoice_type: InvoiceType
    invoice_number: Optional[str] = None
    invoice_date: Optional[datetime] = None
    counterparty_name: Optional[str] = None
    net_amount: Decimal
    vat_amount: Decimal
    counterparty_id: Optional[str] = None
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

    @field_validator("counterparty_id")
    @classmethod
    def validate_counterparty_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.isdigit():
            raise ValueError("מספר עוסק חייב להכיל ספרות בלבד")
        if v is not None and len(v) != 9:
            raise ValueError("מספר עוסק חייב להיות בן 9 ספרות")
        return v


class VatInvoiceResponse(BaseModel):
    id: int
    work_item_id: int
    invoice_type: InvoiceType
    invoice_number: str
    invoice_date: datetime
    counterparty_name: str
    counterparty_id: Optional[str]
    net_amount: Decimal
    vat_amount: Decimal
    expense_category: Optional[ExpenseCategory]
    rate_type: VatRateType = VatRateType.STANDARD
    deduction_rate: Decimal = Decimal("1.0000")
    document_type: Optional[DocumentType] = None
    is_exceptional: bool = False
    created_by: int
    created_at: datetime

    model_config = {"from_attributes": True}


class VatInvoiceListResponse(BaseModel):
    items: list[VatInvoiceResponse]


# ── Status transitions ────────────────────────────────────────────────────────

class SendBackForCorrectionRequest(BaseModel):
    correction_note: str


# ── Filing ────────────────────────────────────────────────────────────────────

class FileVatReturnRequest(BaseModel):
    filing_method: FilingMethod
    override_amount: Optional[Decimal] = None
    override_justification: Optional[str] = None
    submission_reference: Optional[str] = None
    is_amendment: bool = False
    amends_item_id: Optional[int] = None