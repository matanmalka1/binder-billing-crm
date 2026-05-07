from typing import Optional

from pydantic import BaseModel, Field

from app.core.api_types import ApiDateTime, ApiDecimal


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
