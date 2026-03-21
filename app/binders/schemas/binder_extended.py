from datetime import date
from typing import Optional

from pydantic import BaseModel

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
    signals: list[str] = []

    model_config = {"from_attributes": True}


class BinderListResponseExtended(BaseModel):
    items: list[BinderDetailResponse]
    page: int
    page_size: int
    total: int