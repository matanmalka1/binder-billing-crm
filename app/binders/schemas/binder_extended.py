from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from app.binders.models.binder import BinderStatus


class BinderDetailResponse(BaseModel):
    """תצוגה מורחבת עם שדות תפעוליים — לתור העבודה ולוח המחוונים."""
    id: int
    client_id: int
    client_name: Optional[str] = None
    binder_number: str
    period_start: date
    period_end: Optional[date] = None
    status: BinderStatus
    returned_at: Optional[date] = None
    pickup_person_name: Optional[str] = None
    days_active: Optional[int] = None
    work_state: Optional[str] = None
    signals: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class BinderListResponseExtended(BaseModel):
    items: list[BinderDetailResponse]
    page: int
    page_size: int
    total: int


class BinderHistoryEntry(BaseModel):
    old_status: str
    new_status: str
    changed_by: int
    changed_at: str
    notes: str | None = None

    model_config = {"from_attributes": True}


class BinderHistoryResponse(BaseModel):
    binder_id: int
    history: list[BinderHistoryEntry]