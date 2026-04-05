"""Pydantic schema for VAT invoice update requests."""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, field_validator, model_validator

from app.core.api_types import ApiDecimal
from app.vat_reports.models.vat_enums import (
    CounterpartyIdType,
    DocumentType,
    ExpenseCategory,
    VatRateType,
)


class VatInvoiceUpdateRequest(BaseModel):
    net_amount: Optional[ApiDecimal] = None
    vat_amount: Optional[ApiDecimal] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None         # Date — לא DateTime
    counterparty_name: Optional[str] = None
    counterparty_id: Optional[str] = None
    counterparty_id_type: Optional[CounterpartyIdType] = None  # קיים במודל
    expense_category: Optional[ExpenseCategory] = None
    rate_type: Optional[VatRateType] = None
    document_type: Optional[DocumentType] = None

    @field_validator("net_amount")
    @classmethod
    def net_positive(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v <= 0:
            raise ValueError("הסכום נטו חייב להיות חיובי")
        return v

    @field_validator("vat_amount")
    @classmethod
    def vat_non_negative(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < 0:
            raise ValueError("הסכום של המע\"מ לא יכול להיות שלילי")
        return v

    @model_validator(mode="after")
    def validate_counterparty_id(self) -> "VatInvoiceUpdateRequest":
        cid = self.counterparty_id
        cid_type = self.counterparty_id_type
        if cid is None:
            return self
        if cid_type in (CounterpartyIdType.IL_BUSINESS, CounterpartyIdType.IL_PERSONAL):
            if not cid.isdigit() or len(cid) != 9:
                raise ValueError("מספר עוסק / ת\"ז ישראלי חייב להיות 9 ספרות")
        return self
