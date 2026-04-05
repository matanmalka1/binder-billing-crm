from datetime import date
from typing import Optional

from pydantic import BaseModel

from app.binders.models.binder import BinderStatus
from app.core.api_types import ApiDateTime


class BinderDetailResponse(BaseModel):
    """תצוגה מורחבת עם שדות תפעוליים."""
    id: int
    client_id: int
    client_name: Optional[str] = None
    binder_number: str
    period_start: date
    period_end: Optional[date] = None
    status: BinderStatus
    returned_at: Optional[date] = None
    pickup_person_name: Optional[str] = None
    received_at: Optional[date] = None
    # days_in_office: ימים שחלפו מתחילת תקופת הקלסר (period_start → היום).
    # מחושב גם על קלסרים שהוחזרו.
    days_in_office: Optional[int] = None

    model_config = {"from_attributes": True}


class BinderListResponseExtended(BaseModel):
    items: list[BinderDetailResponse]
    page: int
    page_size: int
    total: int


# ── History schemas ───────────────────────────────────────────────────────────
# BinderHistoryEntry and BinderHistoryResponse are defined here (extended view)
# and re-exported so that binders_history.py imports from one place.
# The canonical definitions in binder.py schemas use `changed_at: ApiDateTime`;
# the API router passes datetime objects directly and lets Pydantic serialise
# them as UTC ISO 8601 strings.
# NOTE: binder.py schemas also contain BinderHistoryEntry — those are used
# for the core binder schema module. Import from binder.py for the core
# schemas and from here only for the extended (operations/dashboard) views.

class BinderHistoryEntry(BaseModel):
    old_status: str
    new_status: str
    changed_by: int
    changed_by_name: Optional[str] = None    # enriched by service
    changed_at: ApiDateTime
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class BinderHistoryResponse(BaseModel):
    binder_id: int
    history: list[BinderHistoryEntry]
