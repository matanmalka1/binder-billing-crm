from datetime import date
from typing import Optional

from pydantic import BaseModel

from app.binders.models.binder import BinderStatus


class BinderDetailResponse(BaseModel):
    """תצוגה מורחבת עם שדות תפעוליים."""
    id: int
    client_id: int
    client_name: Optional[str] = None
    client_id_number: Optional[str] = None
    binder_number: str
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    status: BinderStatus
    returned_at: Optional[date] = None
    pickup_person_name: Optional[str] = None
    # days_in_office: ימים שחלפו מתחילת תקופת הקלסר (period_start → היום).
    # מחושב גם על קלסרים שהוחזרו.
    days_in_office: Optional[int] = None

    model_config = {"from_attributes": True}


class BinderListResponseExtended(BaseModel):
    items: list[BinderDetailResponse]
    page: int
    page_size: int
    total: int
