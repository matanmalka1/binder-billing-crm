"""Schemas for annex (schedule) data lines."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

from app.annual_reports.models.annual_report_enums import AnnualReportSchedule


class AnnexDataLineResponse(BaseModel):
    id: int
    annual_report_id: int
    schedule: AnnualReportSchedule
    line_number: int
    data: dict[str, Any]
    notes: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AnnexDataAddRequest(BaseModel):
    data: dict[str, Any]
    notes: Optional[str] = None


class AnnexDataUpdateRequest(BaseModel):
    data: dict[str, Any]
    notes: Optional[str] = None


__all__ = ["AnnexDataLineResponse", "AnnexDataAddRequest", "AnnexDataUpdateRequest"]
