from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.binders.models.binder import BinderStatus
from app.core.api_types import ApiDateTime


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
    # days_active: ימים שחלפו מתחילת תקופת הקלסר (period_start → היום).
    # נקרא days_active ולא days_in_office כי הוא מחושב גם על קלסרים שהוחזרו.
    days_active: Optional[int] = None
    work_state: Optional[str] = None
    signals: list[str] = Field(default_factory=list)

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
