from datetime import date

from pydantic import BaseModel, Field, field_validator

from app.businesses.models.business import BusinessStatus
from app.core.action_schemas import ActionDescriptor
from app.core.api_types import ApiDateTime, PaginatedResponse

# ─── Requests ────────────────────────────────────────────────────────────────


class BusinessCreateRequest(BaseModel):
    """
    יצירת עסק חדש תחת לקוח קיים.
    client_id מועבר ב-URL: POST /clients/{client_id}/businesses
    """

    opened_at: date | None = None
    business_name: str = Field(..., max_length=100)
    notes: str | None = None

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
    שם העסק נדרש לפתיחת פעילות ראשונה.
    """

    opened_at: date | None = None
    business_name: str = Field(..., max_length=100)
    notes: str | None = None

    @field_validator("business_name")
    @classmethod
    def normalize_business_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("יש להזין שם עסק")
        return value


class BusinessUpdateRequest(BaseModel):
    """עדכון פרטי עסק."""

    business_name: str | None = None
    status: BusinessStatus | None = None  # enum
    closed_at: date | None = None


# ─── Responses ────────────────────────────────────────────────────────────────


class BusinessResponse(BaseModel):
    """תגובת עסק."""

    id: int
    client_id: int | None = None
    business_name: str | None = None
    status: BusinessStatus
    opened_at: date
    closed_at: date | None = None
    notes: str | None = None
    created_at: ApiDateTime | None = None
    available_actions: list[ActionDescriptor] = Field(default_factory=list)

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
