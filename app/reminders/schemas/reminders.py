import re
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.reminders.models.reminder import ReminderType, ReminderStatus
from app.core.api_types import ApiDateTime, PaginatedResponse

_DATE_SUFFIX_RE = re.compile(r"\s*\(\d{4}-\d{2}-\d{2}\)$")


class ReminderCreateRequest(BaseModel):
    reminder_type: ReminderType
    target_date: date
    days_before: int = Field(ge=0)
    message: Optional[str] = Field(None, min_length=1)
    client_record_id: Optional[int] = Field(None, gt=0)
    business_id: Optional[int] = Field(None, gt=0)
    binder_id: Optional[int] = Field(None, gt=0)

    @model_validator(mode="after")
    def validate_by_type(self) -> "ReminderCreateRequest":
        t = self.reminder_type
        if t == ReminderType.BINDER_IDLE:
            if not self.binder_id:
                raise ValueError("binder_id נדרש עבור binder_idle")
        elif t == ReminderType.DOCUMENT_MISSING:
            if not self.business_id:
                raise ValueError("business_id נדרש עבור document_missing")
            if not self.message:
                raise ValueError("message נדרש עבור תזכורת מסמך חסר")
        elif t == ReminderType.CUSTOM:
            if not self.client_record_id and not self.business_id:
                raise ValueError("client_record_id או business_id נדרש עבור תזכורת מותאמת אישית")
            if not self.message:
                raise ValueError("message נדרש עבור תזכורת מותאמת אישית")
        return self


class ReminderResponse(BaseModel):
    id: int
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


ReminderListResponse = PaginatedResponse[ReminderResponse]
