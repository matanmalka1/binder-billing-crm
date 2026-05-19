from datetime import date

from pydantic import BaseModel, Field

from app.binders.models.binder import BinderStatus
from app.binders.models.binder_intake_material import MaterialType
from app.core.action_schemas import ActionDescriptor
from app.core.api_types import ApiDateTime

# ── Intake request ────────────────────────────────────────────────────────────


class BinderIntakeMaterialRequest(BaseModel):
    """פריט חומר בודד בתוך אירוע קבלה."""

    material_type: MaterialType
    business_id: int | None = None  # None = כל עסקי הלקוח
    annual_report_id: int | None = None
    vat_report_id: int | None = None
    period_year: int
    period_month_start: int = Field(ge=1, le=12)
    period_month_end: int = Field(ge=1, le=12)
    description: str | None = None


class BinderReceiveRequest(BaseModel):
    """
    קבלת חומרים לקלסר.
    אם binder_number קיים ופעיל — מוסיף intake לקלסר קיים.
    אם לא — יוצר קלסר חדש.
    """

    client_record_id: int  # קלסר שייך ללקוח
    received_at: date  # תאריך קבלת החומרים (ב-intake)
    received_by: int
    open_new_binder: bool = False  # True = סמן קלסר קיים כמלא ופתח חדש
    notes: str | None = None
    materials: list[BinderIntakeMaterialRequest] = Field(default_factory=list)


class BinderReturnRequest(BaseModel):
    pickup_person_name: str | None = None
    returned_by: int | None = None
    returned_at: date | None = None


# ── Core response ─────────────────────────────────────────────────────────────


class BinderResponse(BaseModel):
    id: int
    client_record_id: int
    office_client_number: int | None = None
    client_name: str | None = None  # enriched by service
    client_id_number: str | None = None  # enriched by service
    binder_number: str
    period_start: date | None = None
    period_end: date | None = None
    status: BinderStatus
    returned_at: date | None = None
    pickup_person_name: str | None = None
    notes: str | None = None
    created_at: ApiDateTime
    # ── Derived (computed by service, not stored) ─────────────────────────────
    days_in_office: int | None = None  # today - period_start
    available_actions: list[ActionDescriptor] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class BinderListCounters(BaseModel):
    total: int
    in_office: int
    closed_in_office: int
    ready_for_pickup: int
    returned: int


class BinderListResponse(BaseModel):
    items: list[BinderResponse]
    page: int
    page_size: int
    total: int
    counters: BinderListCounters


# ── Intake responses ──────────────────────────────────────────────────────────


class BinderIntakeMaterialResponse(BaseModel):
    id: int
    intake_id: int
    material_type: MaterialType
    business_id: int | None = None
    annual_report_id: int | None = None
    vat_report_id: int | None = None
    period_year: int
    period_month_start: int
    period_month_end: int
    description: str | None = None
    created_at: ApiDateTime

    model_config = {"from_attributes": True}


class BinderIntakeResponse(BaseModel):
    id: int
    binder_id: int
    received_at: date
    received_by: int
    received_by_name: str | None = None  # enriched by service
    notes: str | None = None
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


class BinderMarkReadyBulkRequest(BaseModel):
    client_record_id: int
    until_period_year: int
    until_period_month: int = Field(ge=1, le=12)


# ── Handover ─────────────────────────────────────────────────────────────────


class BinderHandoverRequest(BaseModel):
    """בקשת מסירת קלסרים מרובים ללקוח בבת אחת."""

    client_record_id: int
    binder_ids: list[int] = Field(min_length=1)
    received_by_name: str
    handed_over_at: date
    until_period_year: int
    until_period_month: int = Field(ge=1, le=12)
    notes: str | None = None


class BinderHandoverResponse(BaseModel):
    id: int
    client_record_id: int
    received_by_name: str
    handed_over_at: date
    until_period_year: int
    until_period_month: int
    binder_ids: list[int]
    notes: str | None = None
    created_at: ApiDateTime

    model_config = {"from_attributes": True}


# ── Status history ────────────────────────────────────────────────────────────


class BinderHistoryEntry(BaseModel):
    old_status: str
    new_status: str
    changed_by: int
    changed_by_name: str | None = None  # enriched by service
    changed_at: ApiDateTime
    notes: str | None = None

    model_config = {"from_attributes": True}


class BinderHistoryResponse(BaseModel):
    binder_id: int
    history: list[BinderHistoryEntry]
