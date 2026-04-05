from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.businesses.models.business import BusinessType, BusinessStatus
from app.core.api_types import ApiDateTime


# ─── Requests ────────────────────────────────────────────────────────────────

class BusinessCreateRequest(BaseModel):
    """
    יצירת עסק חדש תחת לקוח קיים.
    client_id מועבר ב-URL: POST /clients/{client_id}/businesses
    """
    business_type: BusinessType             # enum — לא str חופשי
    opened_at: date
    business_name: Optional[str] = None
    notes: Optional[str] = None
    tax_id_number: Optional[str] = None


class BusinessUpdateRequest(BaseModel):
    """עדכון פרטי עסק."""
    business_name: Optional[str] = None
    business_type: Optional[BusinessType] = None    # enum
    status: Optional[BusinessStatus] = None         # enum
    notes: Optional[str] = None
    closed_at: Optional[date] = None


# ─── Responses ────────────────────────────────────────────────────────────────

class BusinessResponse(BaseModel):
    """תגובת עסק."""
    id: int
    client_id: int
    business_name: Optional[str] = None
    business_type: BusinessType
    status: BusinessStatus
    opened_at: date
    closed_at: Optional[date] = None
    notes: Optional[str] = None
    created_at: Optional[ApiDateTime] = None
    available_actions: list[dict[str, Any]] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class BusinessWithClientResponse(BusinessResponse):
    """תגובת עסק עם פרטי לקוח — לרשימת עסקים כללית."""
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
    page: int
    page_size: int
    total: int
