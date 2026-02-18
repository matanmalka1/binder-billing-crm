from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class AgingBucket(BaseModel):
    """Aging bucket for debt categorization."""
    current: float  # 0-30 days
    days_30: float  # 31-60 days
    days_60: float  # 61-90 days
    days_90_plus: float  # 90+ days


class AgingReportItem(BaseModel):
    """Single client aging report item."""
    client_id: int
    client_name: str
    total_outstanding: float
    current: float
    days_30: float
    days_60: float
    days_90_plus: float
    oldest_invoice_date: Optional[date] = None
    oldest_invoice_days: Optional[int] = None


class AgingReportResponse(BaseModel):
    """Complete aging report response."""
    report_date: date
    total_outstanding: float
    items: list[AgingReportItem]
    summary: dict


class ExportFormat(BaseModel):
    """Export format options."""
    format: str  # "excel" | "pdf"


class ReportExportResponse(BaseModel):
    """Export response with download info."""
    download_url: str
    filename: str
    format: str
    generated_at: datetime