from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.annual_reports.models.annual_report_enums import AnnualReportSchedule
from app.core.api_types import ApiDateTime


class AnnexDataLineResponse(BaseModel):
    id: int
    annual_report_id: int
    schedule: AnnualReportSchedule
    line_number: int
    data: dict[str, Any]
    data_version: int  # נוסף — קיים במודל
    notes: Optional[str] = None
    created_at: ApiDateTime
    updated_at: Optional[ApiDateTime] = None

    model_config = {"from_attributes": True}


class AnnexDataAddRequest(BaseModel):
    data: dict[str, Any]
    notes: Optional[str] = None


class AnnexDataUpdateRequest(BaseModel):
    data: dict[str, Any]
    notes: Optional[str] = None
