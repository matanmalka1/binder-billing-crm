from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class AnnualReportCreateRequest(BaseModel):
    client_id: int
    tax_year: int
    form_type: Optional[str] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None


class AnnualReportTransitionRequest(BaseModel):
    to_stage: str


class AnnualReportSubmitRequest(BaseModel):
    submitted_at: datetime


class AnnualReportResponse(BaseModel):
    id: int
    client_id: int
    tax_year: int
    stage: str
    status: str
    created_at: datetime
    due_date: Optional[date] = None
    submitted_at: Optional[datetime] = None
    form_type: Optional[str] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class AnnualReportListResponse(BaseModel):
    items: list[AnnualReportResponse]
    page: int
    page_size: int
    total: int


class KanbanStageResponse(BaseModel):
    stage: str
    reports: list[dict]


class KanbanResponse(BaseModel):
    stages: list[KanbanStageResponse]