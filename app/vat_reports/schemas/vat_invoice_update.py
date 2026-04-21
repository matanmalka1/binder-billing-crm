"""Pydantic schema for VAT invoice update requests."""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import Field, field_validator

from app.core.api_types import ApiDecimal
from app.vat_reports.models.vat_enums import (
    CounterpartyIdType,
    DocumentType,
    ExpenseCategory,
    VatRateType,
)
from app.vat_reports.schemas.vat_invoice_schema import (
    ANONYMOUS_COUNTERPARTY_ID,
    MAX_COUNTERPARTY_ID_LENGTH,
    MAX_COUNTERPARTY_NAME_LENGTH,
    MAX_INVOICE_NUMBER_LENGTH,
    VatInvoiceValidatorMixin,
)


class VatInvoiceUpdateRequest(VatInvoiceValidatorMixin):
    business_activity_id: Optional[int] = None
    net_amount: Optional[ApiDecimal] = None
    vat_amount: Optional[ApiDecimal] = None
    invoice_number: Optional[str] = Field(default=None, max_length=MAX_INVOICE_NUMBER_LENGTH)
    invoice_date: Optional[date] = None         # Date — לא DateTime
    counterparty_name: Optional[str] = Field(default=None, max_length=MAX_COUNTERPARTY_NAME_LENGTH)
    counterparty_id: Optional[str] = Field(default=None, max_length=MAX_COUNTERPARTY_ID_LENGTH)
    counterparty_id_type: Optional[CounterpartyIdType] = None
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
