from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.reminders.models.reminder import ReminderType, ReminderStatus
from app.core.api_types import ApiDateTime


class ReminderCreateRequest(BaseModel):
    business_id: Optional[int] = Field(None, gt=0)
    client_id: Optional[int] = Field(None, gt=0)
    reminder_type: ReminderType                         # enum — לא str חופשי
    target_date: date
    days_before: int = Field(ge=0)
    message: Optional[str] = Field(None, min_length=1)

    # Domain links — לכל סוג רק אחד ימולא
    binder_id: Optional[int] = Field(None, gt=0)
    charge_id: Optional[int] = Field(None, gt=0)
    tax_deadline_id: Optional[int] = Field(None, gt=0)
    annual_report_id: Optional[int] = Field(None, gt=0)    # קיים במודל
    advance_payment_id: Optional[int] = Field(None, gt=0)  # קיים במודל

    @model_validator(mode="after")
    def validate_by_type(self) -> "ReminderCreateRequest":
        t = self.reminder_type
        # Client-scoped types — derive owner from linked entity, no business_id needed
        if t == ReminderType.TAX_DEADLINE_APPROACHING:
            if not self.client_id:
                raise ValueError("client_id נדרש עבור tax_deadline_approaching")
            if not self.tax_deadline_id:
                raise ValueError("tax_deadline_id נדרש עבור סוג זה")
        elif t == ReminderType.VAT_FILING:
            if not self.tax_deadline_id:
                raise ValueError("tax_deadline_id נדרש עבור vat_filing")
        elif t == ReminderType.BINDER_IDLE:
            if not self.binder_id:
                raise ValueError("binder_id נדרש עבור binder_idle")
        elif t == ReminderType.ANNUAL_REPORT_DEADLINE:
            if not self.annual_report_id:
                raise ValueError("annual_report_id נדרש עבור annual_report_deadline")
        # Business-scoped types — business_id required
        else:
            if not self.business_id:
                raise ValueError("business_id נדרש לסוג תזכורת זה")
            if t == ReminderType.UNPAID_CHARGE and not self.charge_id:
                raise ValueError("charge_id נדרש עבור unpaid_charge")
            if t == ReminderType.ADVANCE_PAYMENT_DUE and not self.advance_payment_id:
                raise ValueError("advance_payment_id נדרש עבור advance_payment_due")
            if t == ReminderType.CUSTOM and not self.message:
                raise ValueError("message נדרש עבור תזכורת מותאמת אישית")
        return self


class ReminderResponse(BaseModel):
    id: int
    business_id: Optional[int] = None
    business_name: Optional[str] = None        # enriched by service
    client_id: Optional[int] = None
    client_name: Optional[str] = None
    reminder_type: ReminderType
    status: ReminderStatus
    target_date: date
    days_before: int
    send_on: date
    message: str
    binder_id: Optional[int] = None
    charge_id: Optional[int] = None
    tax_deadline_id: Optional[int] = None
    annual_report_id: Optional[int] = None     # קיים במודל
    advance_payment_id: Optional[int] = None   # קיים במודל
    created_at: ApiDateTime
    created_by: Optional[int] = None
    sent_at: Optional[ApiDateTime] = None
    canceled_at: Optional[ApiDateTime] = None
    canceled_by: Optional[int] = None          # קיים במודל

    model_config = {"from_attributes": True}


class ReminderListResponse(BaseModel):
    items: list[ReminderResponse]
    page: int
    page_size: int
    total: int
