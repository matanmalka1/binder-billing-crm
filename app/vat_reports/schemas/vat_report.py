"""Pydantic request / response schemas for the VAT Reports module."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
import re

from pydantic import BaseModel, Field, field_validator

from app.common.enums import SubmissionMethod, VatType
from app.vat_reports.models.vat_enums import VatWorkItemStatus


# ── Work Item ─────────────────────────────────────────────────────────────────

class VatWorkItemCreateRequest(BaseModel):
    client_id: int
    period: str                             # "YYYY-MM"
    assigned_to: Optional[int] = None
    mark_pending: bool = False
    pending_materials_note: Optional[str] = None

    @field_validator("period")
    @classmethod
    def validate_period(cls, v: str) -> str:
        if not re.fullmatch(r"\d{4}-(?:0[1-9]|1[0-2])", v):
            raise ValueError("התקופה חייבת להיות בפורמט YYYY-MM")
        return v


class VatWorkItemResponse(BaseModel):
    id: int
    client_id: int
    client_name: Optional[str] = None       # enriched by service
    client_id_number: Optional[str] = None  # enriched by service
    client_status: Optional[str] = None    # enriched by service
    period: str
    period_type: VatType                   # snapshot at creation — immutable historical record
    status: VatWorkItemStatus
    pending_materials_note: Optional[str] = None
    total_output_vat: Decimal
    total_input_vat: Decimal
    net_vat: Decimal
    total_output_net: Decimal              # קיים במודל — שדה 87
    total_input_net: Decimal               # קיים במודל — שדה 66
    final_vat_amount: Optional[Decimal] = None
    is_overridden: bool
    override_justification: Optional[str] = None
    submission_method: Optional[SubmissionMethod] = None  # שם חדש במודל
    filed_at: Optional[datetime] = None
    filed_by: Optional[int] = None
    filed_by_name: Optional[str] = None
    submission_reference: Optional[str] = None
    is_amendment: bool = False
    amends_item_id: Optional[int] = None
    created_by: int
    assigned_to: Optional[int] = None
    assigned_to_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    # Derived — not stored
    submission_deadline: Optional[date] = None
    statutory_deadline: Optional[date] = None
    extended_deadline: Optional[date] = None
    days_until_deadline: Optional[int] = None
    is_overdue: Optional[bool] = None

    model_config = {"from_attributes": True}


class VatWorkItemListResponse(BaseModel):
    items: list[VatWorkItemResponse]
    total: int


class VatPeriodOptionResponse(BaseModel):
    period: str
    label: str
    start_month: int
    end_month: int
    is_opened: bool


class VatPeriodOptionsResponse(BaseModel):
    client_id: int
    year: int
    period_type: VatType
    options: list[VatPeriodOptionResponse]


# ── Status transitions ────────────────────────────────────────────────────────

class SendBackForCorrectionRequest(BaseModel):
    correction_note: str = Field(min_length=1, max_length=1000)

    @field_validator("correction_note")
    @classmethod
    def validate_correction_note(cls, v: str) -> str:
        normalized = v.strip()
        if not normalized:
            raise ValueError("נדרש טקסט תיקון")
        return normalized


# ── Filing ────────────────────────────────────────────────────────────────────

class VatWorkItemLookupResponse(BaseModel):
    id: int
    status: VatWorkItemStatus
    period: str

    model_config = {"from_attributes": True}


class FileVatReturnRequest(BaseModel):
    submission_method: SubmissionMethod    # שם חדש — תואם המודל
    override_amount: Optional[Decimal] = None
    override_justification: Optional[str] = None
    submission_reference: Optional[str] = None
    is_amendment: bool = False
    amends_item_id: Optional[int] = None
