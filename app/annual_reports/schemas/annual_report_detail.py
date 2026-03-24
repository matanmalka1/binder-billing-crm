from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.annual_reports.models.annual_report_credit_point_reason import CreditPointReason
from app.core.api_types import ApiDateTime, ApiDecimal


# ── Credit points (נקודות זיכוי) ─────────────────────────────────────────────

class CreditPointResponse(BaseModel):
    id: int
    annual_report_id: int
    reason: CreditPointReason
    points: ApiDecimal
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class CreditPointCreateRequest(BaseModel):
    reason: CreditPointReason
    points: ApiDecimal = Field(gt=0)
    notes: Optional[str] = None


class CreditPointUpdateRequest(BaseModel):
    points: Optional[ApiDecimal] = Field(None, gt=0)
    notes: Optional[str] = None


# ── Detail (ניכויים ואישורים) ─────────────────────────────────────────────────

class ReportDetailResponse(BaseModel):
    """AnnualReportDetail — ניכויים, אישור לקוח, הערות."""
    report_id: int
    pension_contribution: Optional[ApiDecimal] = None
    donation_amount: Optional[ApiDecimal] = None
    other_credits: Optional[ApiDecimal] = None
    tax_refund_amount: Optional[float] = None
    tax_due_amount: Optional[float] = None
    client_approved_at: Optional[ApiDateTime] = None
    internal_notes: Optional[str] = None
    amendment_reason: Optional[str] = None
    created_at: Optional[ApiDateTime] = None
    updated_at: Optional[ApiDateTime] = None

    model_config = {"from_attributes": True}


class AnnualReportDetailUpdateRequest(BaseModel):
    pension_contribution: Optional[ApiDecimal] = Field(None, ge=0)
    donation_amount: Optional[ApiDecimal] = Field(None, ge=0)
    other_credits: Optional[ApiDecimal] = Field(None, ge=0)
    client_approved_at: Optional[ApiDateTime] = None
    internal_notes: Optional[str] = None
    amendment_reason: Optional[str] = None
