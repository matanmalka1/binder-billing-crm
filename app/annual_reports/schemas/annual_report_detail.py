from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.annual_reports.models.annual_report_credit_point_reason import CreditPointReason


# ── Credit points (נקודות זיכוי) ─────────────────────────────────────────────

class CreditPointResponse(BaseModel):
    id: int
    annual_report_id: int
    reason: CreditPointReason
    points: Decimal
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class CreditPointCreateRequest(BaseModel):
    reason: CreditPointReason
    points: Decimal = Field(gt=0)
    notes: Optional[str] = None


class CreditPointUpdateRequest(BaseModel):
    points: Optional[Decimal] = Field(None, gt=0)
    notes: Optional[str] = None


# ── Detail (ניכויים ואישורים) ─────────────────────────────────────────────────

class ReportDetailResponse(BaseModel):
    """AnnualReportDetail — ניכויים, אישור לקוח, הערות."""
    report_id: int
    pension_contribution: Optional[Decimal] = None
    donation_amount: Optional[Decimal] = None
    other_credits: Optional[Decimal] = None
    client_approved_at: Optional[datetime] = None
    internal_notes: Optional[str] = None
    amendment_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # נקודות זיכוי — ממודל נפרד
    credit_points: list[CreditPointResponse] = []

    model_config = {"from_attributes": True}


class AnnualReportDetailUpdateRequest(BaseModel):
    pension_contribution: Optional[Decimal] = Field(None, ge=0)
    donation_amount: Optional[Decimal] = Field(None, ge=0)
    other_credits: Optional[Decimal] = Field(None, ge=0)
    client_approved_at: Optional[datetime] = None
    internal_notes: Optional[str] = None
    amendment_reason: Optional[str] = None