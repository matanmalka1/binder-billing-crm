from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.clients.models.client import ClientStatus, IdNumberType
from app.common.enums import VatType
from app.core.api_types import ApiDateTime
from app.utils.id_validation import validate_israeli_id_checksum


# ─── Requests ────────────────────────────────────────────────────────────────

class ClientCreateRequest(BaseModel):
    """
    יצירת לקוח חדש — פרטי זהות בלבד.
    שדות עסקיים (client_type, opened_at וכו') נמצאים ב-BusinessCreateRequest.
    """
    full_name: str
    id_number: str
    id_number_type: IdNumberType = IdNumberType.INDIVIDUAL
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address_street: Optional[str] = None
    address_building_number: Optional[str] = None
    address_apartment: Optional[str] = None
    address_city: Optional[str] = None
    address_zip_code: Optional[str] = None
    vat_reporting_frequency: Optional[VatType] = None

    @field_validator("id_number")
    @classmethod
    def normalize_id_number(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("יש להזין מספר מזהה")
        return v

    @model_validator(mode="after")
    def validate_id_checksum(self) -> "ClientCreateRequest":
        if self.id_number_type in {IdNumberType.INDIVIDUAL, IdNumberType.CORPORATION}:
            if not self.id_number.isdigit():
                raise ValueError("מספר זהות/ח.פ חייב להכיל ספרות בלבד")
            if len(self.id_number) != 9:
                raise ValueError("מספר זהות/ח.פ חייב להכיל בדיוק 9 ספרות")

        if self.id_number_type == IdNumberType.INDIVIDUAL:
            if not validate_israeli_id_checksum(self.id_number):
                raise ValueError("מספר זהות אינו תקין")
        return self


class ClientUpdateRequest(BaseModel):
    """עדכון פרטי זהות בלבד."""
    full_name: Optional[str] = None
    status: Optional[ClientStatus] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address_street: Optional[str] = None
    address_building_number: Optional[str] = None
    address_apartment: Optional[str] = None
    address_city: Optional[str] = None
    address_zip_code: Optional[str] = None
    vat_reporting_frequency: Optional[VatType] = None


# ─── Responses ────────────────────────────────────────────────────────────────

class ClientResponse(BaseModel):
    """תגובת לקוח — פרטי זהות בלבד."""
    id: int
    full_name: str
    id_number: str
    id_number_type: Optional[IdNumberType] = None
    status: ClientStatus = ClientStatus.ACTIVE
    phone: Optional[str] = None
    email: Optional[str] = None
    address_street: Optional[str] = None
    address_building_number: Optional[str] = None
    address_apartment: Optional[str] = None
    address_city: Optional[str] = None
    address_zip_code: Optional[str] = None
    notes: Optional[str] = None
    vat_reporting_frequency: Optional[VatType] = None
    created_at: Optional[ApiDateTime] = None
    updated_at: Optional[ApiDateTime] = None
    # ── Enriched fields (set by API layer, not stored on Client) ──────────────
    primary_business_type: Optional[str] = None
    active_binder_number: Optional[str] = None

    model_config = {"from_attributes": True}


class ClientListResponse(BaseModel):
    items: list[ClientResponse]
    page: int
    page_size: int
    total: int


# ─── Conflict info ────────────────────────────────────────────────────────────

class ActiveClientSummary(BaseModel):
    """סיכום לקוח פעיל — מוחזר בתגובת CLIENT.CONFLICT."""
    id: int
    full_name: str
    id_number: str

    model_config = {"from_attributes": True}


class DeletedClientSummary(BaseModel):
    """סיכום לקוח מחוק — מוחזר בתגובת CLIENT.DELETED_EXISTS."""
    id: int
    full_name: str
    id_number: str
    deleted_at: ApiDateTime

    model_config = {"from_attributes": True}


class ClientConflictInfo(BaseModel):
    """
    מידע מלא על קונפליקטים לת.ז. נתונה.
    מוחזר כחלק מתגובת 409.
    """
    id_number: str
    active_clients: list[ActiveClientSummary]
    deleted_clients: list[DeletedClientSummary]


class ClientImportError(BaseModel):
    row: int
    error: str


class ClientImportResponse(BaseModel):
    created: int
    total_rows: int
    errors: list[ClientImportError]
