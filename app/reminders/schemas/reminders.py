import re
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.reminders.models.reminder import ReminderType, ReminderStatus
from app.core.api_types import ApiDateTime

_DATE_SUFFIX_RE = re.compile(r"\s*\(\d{4}-\d{2}-\d{2}\)$")


class ReminderCreateRequest(BaseModel):
    reminder_type: ReminderType
    target_date: date
    days_before: int = Field(ge=0)
    message: Optional[str] = Field(None, min_length=1)

    # Anchors — validated per type below
    client_record_id: Optional[int] = Field(None, gt=0)
    business_id: Optional[int] = Field(None, gt=0)

    # Domain links — at most one set per reminder, matched to reminder_type
    binder_id: Optional[int] = Field(None, gt=0)
    charge_id: Optional[int] = Field(None, gt=0)
    tax_deadline_id: Optional[int] = Field(None, gt=0)
    annual_report_id: Optional[int] = Field(None, gt=0)
    advance_payment_id: Optional[int] = Field(None, gt=0)

    @model_validator(mode="after")
    def validate_by_type(self) -> "ReminderCreateRequest":
        t = self.reminder_type

        if t == ReminderType.TAX_DEADLINE_APPROACHING:
            if not self.client_record_id:
                raise ValueError("client_record_id נדרש עבור tax_deadline_approaching")
            if not self.tax_deadline_id:
                raise ValueError("tax_deadline_id נדרש עבור סוג זה")

        elif t == ReminderType.VAT_FILING:
            # client_record_id resolved from tax_deadline in the factory
            if not self.tax_deadline_id:
                raise ValueError("tax_deadline_id נדרש עבור vat_filing")

        elif t == ReminderType.BINDER_IDLE:
            # client_record_id resolved from binder in the factory
            if not self.binder_id:
                raise ValueError("binder_id נדרש עבור binder_idle")

        elif t == ReminderType.ANNUAL_REPORT_DEADLINE:
            # client_record_id resolved from annual_report in the factory
            if not self.annual_report_id:
                raise ValueError("annual_report_id נדרש עבור annual_report_deadline")

        elif t == ReminderType.UNPAID_CHARGE:
            # client_record_id required explicitly; business_id is optional context
            if not self.client_record_id:
                raise ValueError("client_record_id נדרש עבור unpaid_charge")
            if not self.charge_id:
                raise ValueError("charge_id נדרש עבור unpaid_charge")

        elif t == ReminderType.ADVANCE_PAYMENT_DUE:
            # client_record_id resolved from business in the factory
            if not self.business_id:
                raise ValueError("business_id נדרש עבור advance_payment_due")
            if not self.advance_payment_id:
                raise ValueError("advance_payment_id נדרש עבור advance_payment_due")

        elif t == ReminderType.DOCUMENT_MISSING:
            # client_record_id resolved from business in the factory
            if not self.business_id:
                raise ValueError("business_id נדרש עבור document_missing")
            if not self.message:
                raise ValueError("message נדרש עבור תזכורת מסמך חסר")

        elif t == ReminderType.CUSTOM:
            # client_record_id is the primary anchor; business_id is optional context
            if not self.client_record_id and not self.business_id:
                raise ValueError("client_record_id או business_id נדרש עבור תזכורת מותאמת אישית")
            if not self.message:
                raise ValueError("message נדרש עבור תזכורת מותאמת אישית")

        return self


class ReminderResponse(BaseModel):
    id: int
    # Populated by the query layer from client_record_id — not an ORM column.
    client_record_id: Optional[int] = None
    client_name: Optional[str] = None
    client_id_number: Optional[str] = None
    office_client_number: Optional[int] = None
    business_id: Optional[int] = None
    business_name: Optional[str] = None
    reminder_type: ReminderType
    status: ReminderStatus
    target_date: date
    days_before: int
    send_on: date
    message: str
    binder_id: Optional[int] = None
    charge_id: Optional[int] = None
    tax_deadline_id: Optional[int] = None
    annual_report_id: Optional[int] = None
    advance_payment_id: Optional[int] = None
    created_at: ApiDateTime
    created_by: Optional[int] = None
    sent_at: Optional[ApiDateTime] = None
    canceled_at: Optional[ApiDateTime] = None
    canceled_by: Optional[int] = None
    display_label: Optional[str] = None

    @field_validator("message", mode="before")
    @classmethod
    def strip_date_suffix(cls, v: str) -> str:
        return _DATE_SUFFIX_RE.sub("", v)

    model_config = {"from_attributes": True}


class ReminderListResponse(BaseModel):
    items: list[ReminderResponse]
    page: int
    page_size: int
    total: int
