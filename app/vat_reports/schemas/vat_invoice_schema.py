"""Pydantic schemas for VAT Invoice entities."""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, field_validator, model_validator

from app.core.api_types import ApiDecimal
from app.vat_reports.models.vat_enums import (
    CounterpartyIdType,
    DocumentType,
    ExpenseCategory,
    InvoiceType,
    VatRateType,
)


class VatInvoiceCreateRequest(BaseModel):
    invoice_type: InvoiceType
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None    # Date — לא DateTime
    counterparty_name: Optional[str] = None
    net_amount: ApiDecimal
    vat_amount: ApiDecimal
    counterparty_id: Optional[str] = None
    counterparty_id_type: Optional[CounterpartyIdType] = None  
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
    net_amount: ApiDecimal
    vat_amount: ApiDecimal
    expense_category: Optional[ExpenseCategory] = None
    rate_type: VatRateType
    deduction_rate: ApiDecimal
    is_exceptional: bool
    created_by: int
    created_at: date                       # Date במודל
    # Non-null only on create response — True when annual turnover crosses 80% of OSEK PATUR ceiling
    ceiling_warning: bool = False

    model_config = {"from_attributes": True}


class VatInvoiceListResponse(BaseModel):
    items: list[VatInvoiceResponse]
