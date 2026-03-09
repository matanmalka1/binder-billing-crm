from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ReportDetailResponse(BaseModel):
    """Response for the AnnualReportDetail sub-entity (tax amounts, internal notes)."""
    report_id: int
    tax_refund_amount: Optional[float] = None
    tax_due_amount: Optional[float] = None
    client_approved_at: Optional[datetime] = None
    credit_points: Optional[float] = None
    pension_contribution: Optional[float] = None
    donation_amount: Optional[float] = None
    other_credits: Optional[float] = None
    internal_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AnnualReportDetailUpdateRequest(BaseModel):
    tax_refund_amount: Optional[float] = None
    tax_due_amount: Optional[float] = None
    client_approved_at: Optional[datetime] = None
    internal_notes: Optional[str] = None
    credit_points: Optional[float] = None
    pension_contribution: Optional[float] = None
    donation_amount: Optional[float] = None
    other_credits: Optional[float] = None