from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ─── Requests ────────────────────────────────────────────────────────────────

class BusinessCreateRequest(BaseModel):
    """
    יצירת עסק חדש תחת לקוח קיים.
    client_id מועבר ב-URL: POST /clients/{client_id}/businesses
    """
    business_type: str  # osek_patur, osek_murshe, company, employee
    opened_at: date
    business_name: Optional[str] = None
    notes: Optional[str] = None


class BusinessUpdateRequest(BaseModel):
    """עדכון פרטי עסק."""
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    status: Optional[str] = None
    primary_binder_number: Optional[str] = None
    notes: Optional[str] = None
    closed_at: Optional[date] = None


class BulkBusinessActionRequest(BaseModel):
    business_ids: list[int] = Field(min_length=1)
    action: Literal["freeze", "close", "activate"]


# ─── Responses ────────────────────────────────────────────────────────────────

class BusinessResponse(BaseModel):
    """תגובת עסק — כולל פרטי לקוח מצורפים."""
    id: int
    client_id: int
    business_name: Optional[str] = None
    business_type: str
    status: str
    primary_binder_number: Optional[str] = None
    opened_at: date
    closed_at: Optional[date] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    available_actions: list[dict[str, Any]] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class BusinessWithClientResponse(BusinessResponse):
    """תגובת עסק עם פרטי לקוח מצורפים — לרשימת עסקים כללית."""
    client_full_name: str
    client_id_number: str

    model_config = {"from_attributes": True}


class BusinessListResponse(BaseModel):
    items: list[BusinessWithClientResponse]
    page: int
    page_size: int
    total: int


class ClientBusinessesResponse(BaseModel):
    """רשימת עסקים של לקוח ספציפי."""
    client_id: int
    items: list[BusinessResponse]
    total: int


# ─── Bulk ─────────────────────────────────────────────────────────────────────

class BulkBusinessFailedItem(BaseModel):
    id: int
    error: str


class BulkBusinessActionResponse(BaseModel):
    succeeded: list[int]
    failed: list[BulkBusinessFailedItem]
