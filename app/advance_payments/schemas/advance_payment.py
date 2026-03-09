from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.advance_payments.models.advance_payment import AdvancePaymentStatus


class AdvancePaymentRow(BaseModel):
    id: int
    client_id: int
    tax_deadline_id: Optional[int] = None
    month: int
    year: int
    expected_amount: Optional[float] = None
    paid_amount: Optional[float] = None
    status: AdvancePaymentStatus
    due_date: date
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True, "use_enum_values": True}


class AdvancePaymentListResponse(BaseModel):
    items: list[AdvancePaymentRow]
    page: int
    page_size: int
    total: int


class AdvancePaymentUpdateRequest(BaseModel):
    paid_amount: Optional[float] = None
    expected_amount: Optional[float] = None
    status: Optional[AdvancePaymentStatus] = None
    notes: Optional[str] = Field(None, max_length=500)

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "AdvancePaymentUpdateRequest":
        if (
            self.paid_amount is None
            and self.expected_amount is None
            and self.status is None
            and self.notes is None
        ):
            raise ValueError("יש לספק לפחות שדה אחד לעדכון")
        return self


class AdvancePaymentCreateRequest(BaseModel):
    client_id: int
    year: int
    month: int = Field(..., ge=1, le=12)
    due_date: date
    expected_amount: Optional[float] = None
    paid_amount: Optional[float] = None
    tax_deadline_id: Optional[int] = None
    notes: Optional[str] = Field(None, max_length=500)

    model_config = {"json_schema_extra": {"example": {
        "client_id": 123,
        "year": 2026,
        "month": 3,
        "due_date": "2026-03-15",
        "expected_amount": 2500.0,
    }}}


class AdvancePaymentSuggestionResponse(BaseModel):
    client_id: int
    year: int
    suggested_amount: Optional[Decimal] = None
    has_data: bool


class AdvancePaymentOverviewRow(BaseModel):
    id: int
    client_id: int
    client_name: str
    month: int
    year: int
    expected_amount: Optional[float] = None
    paid_amount: Optional[float] = None
    status: AdvancePaymentStatus
    due_date: date

    model_config = {"from_attributes": True, "use_enum_values": True}


class AdvancePaymentOverviewResponse(BaseModel):
    items: list[AdvancePaymentOverviewRow]
    page: int
    page_size: int
    total: int
