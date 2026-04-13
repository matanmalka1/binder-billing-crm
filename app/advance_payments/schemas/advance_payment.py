from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, computed_field, model_validator

from app.advance_payments.models.advance_payment import AdvancePaymentStatus, PaymentMethod
from app.advance_payments.services.constants import (
    BIMONTHLY_START_MONTHS,
    SUPPORTED_PERIOD_MONTH_COUNTS,
    parse_period_month,
)
from app.core.api_types import ApiDateTime, ApiDecimal


class AdvancePaymentRow(BaseModel):
    id: int
    client_id: int
    business_name: Optional[str] = None
    period: str                          # "YYYY-MM"
    period_months_count: int             # 1=חודשי, 2=דו-חודשי
    due_date: date
    expected_amount: Optional[ApiDecimal] = None
    paid_amount: Optional[ApiDecimal] = None
    status: AdvancePaymentStatus
    paid_at: Optional[ApiDateTime] = None
    payment_method: Optional[PaymentMethod] = None
    annual_report_id: Optional[int] = None
    notes: Optional[str] = None
    created_at: ApiDateTime
    updated_at: Optional[ApiDateTime] = None

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
    period: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$")  # "YYYY-MM"
    period_months_count: int = Field(1, ge=1, le=2)                 # 1=חודשי, 2=דו-חודשי
    due_date: date
    expected_amount: Optional[ApiDecimal] = Field(None, ge=0)
    paid_amount: Optional[ApiDecimal] = Field(None, ge=0)
    payment_method: Optional[PaymentMethod] = None
    annual_report_id: Optional[int] = None
    notes: Optional[str] = Field(None, max_length=500)

    @model_validator(mode="after")
    def validate_period_for_frequency(self) -> "AdvancePaymentCreateRequest":
        if self.period_months_count not in SUPPORTED_PERIOD_MONTH_COUNTS:
            raise ValueError("period_months_count לא נתמך")
        if self.period_months_count != 2:
            return self

        month = parse_period_month(self.period)
        if month not in BIMONTHLY_START_MONTHS:
            raise ValueError("מקדמה דו-חודשית חייבת להתחיל בחודש אי-זוגי")
        return self

    model_config = {"json_schema_extra": {"example": {
        "period": "2026-03",
        "period_months_count": 1,
        "due_date": "2026-04-15",
        "expected_amount": "2500.00",
    }}}


class AdvancePaymentUpdateRequest(BaseModel):
    paid_amount: Optional[ApiDecimal] = Field(None, ge=0)
    expected_amount: Optional[ApiDecimal] = Field(None, ge=0)
    status: Optional[AdvancePaymentStatus] = None
    paid_at: Optional[ApiDateTime] = None
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
    client_id: int
    year: int
    suggested_amount: Optional[ApiDecimal] = None
    has_data: bool


class AdvancePaymentOverviewRow(BaseModel):
    id: int
    client_id: int
    business_name: str
    period: str
    period_months_count: int
    due_date: date
    expected_amount: Optional[ApiDecimal] = None
    paid_amount: Optional[ApiDecimal] = None
    status: AdvancePaymentStatus

    @computed_field
    @property
    def delta(self) -> Optional[Decimal]:
        """expected - paid. שלילי = חוסר תשלום."""
        if self.expected_amount is None or self.paid_amount is None:
            return None
        return self.expected_amount - self.paid_amount

    model_config = {"from_attributes": True, "use_enum_values": True}


class AdvancePaymentOverviewResponse(BaseModel):
    items: list[AdvancePaymentOverviewRow]
    page: int
    page_size: int
    total: int
    total_expected: Optional[ApiDecimal] = None
    total_paid: Optional[ApiDecimal] = None
    collection_rate: Optional[float] = None  # 0.0–100.0


class AnnualKPIResponse(BaseModel):
    client_id: int
    year: int
    total_expected: ApiDecimal
    total_paid: ApiDecimal
    collection_rate: float  # 0.0–100.0
    overdue_count: int
    on_time_count: int


class MonthlyChartRow(BaseModel):
    period: str          # "YYYY-MM"
    period_months_count: int
    expected_amount: ApiDecimal
    paid_amount: ApiDecimal
    overdue_amount: ApiDecimal


class ChartDataResponse(BaseModel):
    client_id: int
    year: int
    months: list[MonthlyChartRow]


class GenerateScheduleRequest(BaseModel):
    year: int
    period_months_count: int = Field(1, ge=1, le=2)  # 1=חודשי, 2=דו-חודשי


class GenerateScheduleResponse(BaseModel):
    created: int
    skipped: int
