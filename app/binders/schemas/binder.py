from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.binders.models.binder import BinderStatus
from app.binders.models.binder_intake_material import MaterialType
from app.core.api_types import ApiDateTime


# ── Intake request ────────────────────────────────────────────────────────────

class BinderIntakeMaterialRequest(BaseModel):
    """פריט חומר בודד בתוך אירוע קבלה."""
    material_type: MaterialType
    business_id: Optional[int] = None        # None = כל עסקי הלקוח
    annual_report_id: Optional[int] = None
    description: Optional[str] = None


class BinderReceiveRequest(BaseModel):
    """
    קבלת חומרים לקלסר.
    אם binder_number קיים ופעיל — מוסיף intake לקלסר קיים.
    אם לא — יוצר קלסר חדש.
    """
    client_id: int                            # קלסר שייך ללקוח
    period_start: date = Field(default_factory=date.today)  # תחילת תקופת הקלסר
    received_at: date                         # תאריך קבלת החומרים (ב-intake)
    received_by: int
    open_new_binder: bool = False             # True = סמן קלסר קיים כמלא ופתח חדש
    notes: Optional[str] = None
    materials: list[BinderIntakeMaterialRequest] = Field(default_factory=list)


class BinderReturnRequest(BaseModel):
    pickup_person_name: Optional[str] = None
    returned_by: Optional[int] = None
    returned_at: Optional[date] = None


# ── Core response ─────────────────────────────────────────────────────────────

class BinderResponse(BaseModel):
    id: int
    client_id: int
    client_name: Optional[str] = None        # enriched by service
    binder_number: str
    period_start: date
    period_end: Optional[date] = None
    status: BinderStatus
    is_full: bool = False
    returned_at: Optional[date] = None
    pickup_person_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: ApiDateTime
    # ── Derived from first intake (enriched by service) ───────────────────────
    binder_type: Optional[str] = None        # material_type of first intake material
    received_at: Optional[date] = None       # received_at of first intake
    # ── Derived (computed by service, not stored) ─────────────────────────────
    days_in_office: Optional[int] = None     # today - period_start
    work_state: Optional[str] = None
    signals: list[str] = Field(default_factory=list)
    available_actions: list[dict[str, Any]] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class BinderListResponse(BaseModel):
    items: list[BinderResponse]
    page: int
    page_size: int
    total: int


# ── Intake responses ──────────────────────────────────────────────────────────

class BinderIntakeMaterialResponse(BaseModel):
    id: int
    intake_id: int
    material_type: MaterialType
    business_id: Optional[int] = None
    annual_report_id: Optional[int] = None
    description: Optional[str] = None
    created_at: ApiDateTime

    model_config = {"from_attributes": True}


class BinderIntakeResponse(BaseModel):
    id: int
    binder_id: int
    received_at: date
    received_by: int
    received_by_name: Optional[str] = None   # enriched by service
    notes: Optional[str] = None
    created_at: ApiDateTime
    materials: list[BinderIntakeMaterialResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class BinderIntakeListResponse(BaseModel):
    binder_id: int
    intakes: list[BinderIntakeResponse]


class BinderReceiveResult(BaseModel):
    """תוצאת קבלת חומרים — binder + intake."""
    binder: BinderResponse
    intake: BinderIntakeResponse
    is_new_binder: bool


# ── Status history ────────────────────────────────────────────────────────────

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
