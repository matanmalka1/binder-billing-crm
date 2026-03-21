from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, computed_field, model_validator

from app.advance_payments.models.advance_payment import AdvancePaymentStatus, PaymentMethod


class AdvancePaymentRow(BaseModel):
    id: int
    business_id: int
    period: str                          # "YYYY-MM"
    period_months_count: int             # 1=חודשי, 2=דו-חודשי
    due_date: date
    expected_amount: Optional[Decimal] = None
    paid_amount: Optional[Decimal] = None
    status: AdvancePaymentStatus
    paid_at: Optional[datetime] = None
    payment_method: Optional[PaymentMethod] = None
    annual_report_id: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    @computed_field
    @property
    def delta(self) -> Optional[Decimal]:
        """expected - paid. שלילי = חוסר תשלום."""
        if self.expected_amount is None or self.paid_amount is None:
            return None
        return self.expected_amount - self.paid_amount

    model_config = {"from_attributes": True, "use_enum_values": True}


class AdvancePaymentListResponse(BaseModel):
    items: list[AdvancePaymentRow]
    page: int
    page_size: int
    total: int


class AdvancePaymentCreateRequest(BaseModel):
    business_id: int
    period: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$")  # "YYYY-MM"
    period_months_count: int = Field(1, ge=1, le=2)                 # 1=חודשי, 2=דו-חודשי
    due_date: date
    expected_amount: Optional[Decimal] = Field(None, ge=0)
    paid_amount: Optional[Decimal] = Field(None, ge=0)
    payment_method: Optional[PaymentMethod] = None
    annual_report_id: Optional[int] = None
    notes: Optional[str] = Field(None, max_length=500)

    model_config = {"json_schema_extra": {"example": {
        "business_id": 123,
        "period": "2026-03",
        "period_months_count": 1,
        "due_date": "2026-04-15",
        "expected_amount": "2500.00",
    }}}


class AdvancePaymentUpdateRequest(BaseModel):
    paid_amount: Optional[Decimal] = Field(None, ge=0)
    expected_amount: Optional[Decimal] = Field(None, ge=0)
    status: Optional[AdvancePaymentStatus] = None
    paid_at: Optional[datetime] = None
    payment_method: Optional[PaymentMethod] = None
    notes: Optional[str] = Field(None, max_length=500)

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "AdvancePaymentUpdateRequest":
        if all(v is None for v in [
            self.paid_amount, self.expected_amount,
            self.status, self.paid_at,
            self.payment_method, self.notes,
        ]):
            raise ValueError("יש לספק לפחות שדה אחד לעדכון")
        return self


class AdvancePaymentSuggestionResponse(BaseModel):
    business_id: int
    year: int
    suggested_amount: Optional[Decimal] = None
    has_data: bool


class AdvancePaymentOverviewRow(BaseModel):
    id: int
    business_id: int
    business_name: str
    period: str
    period_months_count: int
    due_date: date
    expected_amount: Optional[Decimal] = None
    paid_amount: Optional[Decimal] = None
    status: AdvancePaymentStatus

    model_config = {"from_attributes": True, "use_enum_values": True}


class AdvancePaymentOverviewResponse(BaseModel):
    items: list[AdvancePaymentOverviewRow]
    page: int
    page_size: int
    total: int
    total_expected: Optional[Decimal] = None
    total_paid: Optional[Decimal] = None
    collection_rate: Optional[float] = None  # 0.0–100.0


class AnnualKPIResponse(BaseModel):
    business_id: int
    year: int
    total_expected: Decimal
    total_paid: Decimal
    collection_rate: float  # 0.0–100.0
    overdue_count: int
    on_time_count: int


class MonthlyChartRow(BaseModel):
    period: str          # "YYYY-MM"
    expected_amount: Decimal
    paid_amount: Decimal
    overdue_amount: Decimal


class ChartDataResponse(BaseModel):
    business_id: int
    year: int
    months: list[MonthlyChartRow]


class GenerateScheduleRequest(BaseModel):
    business_id: int
    year: int
    period_months_count: int = Field(1, ge=1, le=2)  # 1=חודשי, 2=דו-חודשי


class GenerateScheduleResponse(BaseModel):
    created: int
    skipped: int