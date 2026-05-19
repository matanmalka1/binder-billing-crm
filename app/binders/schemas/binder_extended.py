from datetime import date

from pydantic import BaseModel

from app.binders.models.binder import BinderStatus
from app.core.api_types import PaginatedResponse


class BinderDetailResponse(BaseModel):
    """תצוגה מורחבת עם שדות תפעוליים."""

    id: int
    client_record_id: int
    office_client_number: int | None = None
    client_name: str | None = None
    client_id_number: str | None = None
    binder_number: str
    period_start: date | None = None
    period_end: date | None = None
    status: BinderStatus
    returned_at: date | None = None
    pickup_person_name: str | None = None
    # days_in_office: ימים שחלפו מתחילת תקופת הקלסר (period_start → היום).
    # מחושב גם על קלסרים שהוחזרו.
    days_in_office: int | None = None

    model_config = {"from_attributes": True}


BinderListResponseExtended = PaginatedResponse[BinderDetailResponse]
