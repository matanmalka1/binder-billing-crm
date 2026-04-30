from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from app.businesses.models.business import BusinessStatus
from app.core.api_types import ApiDateTime, PaginatedResponse


# ─── Requests ────────────────────────────────────────────────────────────────

class BusinessCreateRequest(BaseModel):
    """
    יצירת עסק חדש תחת לקוח קיים.
    client_id מועבר ב-URL: POST /clients/{client_id}/businesses
    """
    opened_at: Optional[date] = None
    business_name: str = Field(..., max_length=100)
    notes: Optional[str] = None

    @field_validator("business_name")
    @classmethod
    def normalize_business_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("יש להזין שם עסק")
        return value


class ClientBusinessCreateRequest(BaseModel):
    """
    פרטי עסק במסגרת פתיחת לקוח חדש.
    שם העסק אופציונלי — אם ריק, ישתמש המערכת בשם הלקוח.
    """
    opened_at: Optional[date] = None
    business_name: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None

    @field_validator("business_name")
    @classmethod
    def normalize_business_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None


class BusinessUpdateRequest(BaseModel):
    """עדכון פרטי עסק."""
    business_name: Optional[str] = None
    status: Optional[BusinessStatus] = None         # enum
    closed_at: Optional[date] = None


# ─── Responses ────────────────────────────────────────────────────────────────

class BusinessResponse(BaseModel):
    """תגובת עסק."""
    id: int
    client_id: Optional[int] = None
    business_name: Optional[str] = None
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


BusinessListResponse = PaginatedResponse[BusinessWithClientResponse]


class ClientBusinessesResponse(BaseModel):
    """רשימת עסקים של לקוח ספציפי."""
    client_id: int
    items: list[BusinessResponse]
    page: int
    page_size: int
    total: int
