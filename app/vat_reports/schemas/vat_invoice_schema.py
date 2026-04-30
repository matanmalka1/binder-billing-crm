"""Pydantic schemas for VAT Invoice entities."""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.api_types import ApiDecimal
from app.utils.id_validation import validate_israeli_id_checksum
from app.vat_reports.models.vat_enums import (
    CounterpartyIdType,
    DocumentType,
    ExpenseCategory,
    InvoiceType,
    VatRateType,
)

MAX_INVOICE_NUMBER_LENGTH = 100
MAX_COUNTERPARTY_NAME_LENGTH = 255
MAX_COUNTERPARTY_ID_LENGTH = 32
ANONYMOUS_COUNTERPARTY_ID = "999999999"


class VatInvoiceValidatorMixin(BaseModel):
    """Shared field validators for VAT invoice create and update schemas."""

    counterparty_id: Optional[str] = None
    counterparty_id_type: Optional[CounterpartyIdType] = None

    @field_validator("invoice_number", "counterparty_name", "counterparty_id", check_fields=False)
    @classmethod
    def normalize_optional_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        normalized = v.strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_counterparty_id(self) -> "VatInvoiceValidatorMixin":
        cid = self.counterparty_id
        cid_type = self.counterparty_id_type

        if cid is None and cid_type is None:
            return self

        if cid_type in (CounterpartyIdType.IL_BUSINESS, CounterpartyIdType.IL_PERSONAL):
            if cid is None:
                raise ValueError("יש להזין מספר מזהה ישראלי כאשר סוג המזהה הוא ישראלי")
            if not cid.isdigit() or len(cid) != 9:
                raise ValueError("מספר עוסק / ת\"ז ישראלי חייב להיות 9 ספרות")
            if not validate_israeli_id_checksum(cid):
                raise ValueError("מספר עוסק / ת\"ז ישראלי אינו תקין")
            return self

        if cid_type == CounterpartyIdType.FOREIGN:
            if cid is None:
                raise ValueError("יש להזין מזהה צד נגדי עבור מזהה זר")
            return self

        if cid_type == CounterpartyIdType.ANONYMOUS:
            if cid != ANONYMOUS_COUNTERPARTY_ID:
                raise ValueError('עבור מזהה אנונימי יש להזין "999999999"')

        return self


class VatInvoiceCreateRequest(VatInvoiceValidatorMixin):
    invoice_type: InvoiceType
    business_activity_id: Optional[int] = None
    invoice_number: Optional[str] = Field(default=None, max_length=MAX_INVOICE_NUMBER_LENGTH)
    invoice_date: Optional[date] = None    # Date — לא DateTime
    counterparty_name: Optional[str] = Field(default=None, max_length=MAX_COUNTERPARTY_NAME_LENGTH)
    net_amount: ApiDecimal
    vat_amount: Optional[ApiDecimal] = None
    counterparty_id: Optional[str] = Field(default=None, max_length=MAX_COUNTERPARTY_ID_LENGTH)
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
    def vat_non_negative(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < 0:
            raise ValueError("הסכום של המע\"מ לא יכול להיות שלילי")
        return v


class VatInvoiceResponse(BaseModel):
    id: int
    work_item_id: int
    business_activity_id: Optional[int] = None
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
