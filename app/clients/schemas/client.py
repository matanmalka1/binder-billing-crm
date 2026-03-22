from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.clients.models.client import IdNumberType
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

    @field_validator("id_number")
    @classmethod
    def validate_id_number_format(cls, v: str) -> str:
        v = v.strip()
        if not v.isdigit():
            raise ValueError("מספר זהות/ח.פ חייב להכיל ספרות בלבד")
        if len(v) != 9:
            raise ValueError("מספר זהות/ח.פ חייב להכיל בדיוק 9 ספרות")
        return v

    @model_validator(mode="after")
    def validate_id_checksum(self) -> "ClientCreateRequest":
        if self.id_number_type == IdNumberType.INDIVIDUAL:
            if not validate_israeli_id_checksum(self.id_number):
                raise ValueError("מספר זהות אינו תקין")
        return self


class ClientUpdateRequest(BaseModel):
    """עדכון פרטי זהות בלבד."""
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address_street: Optional[str] = None
    address_building_number: Optional[str] = None
    address_apartment: Optional[str] = None
    address_city: Optional[str] = None
    address_zip_code: Optional[str] = None


# ─── Responses ────────────────────────────────────────────────────────────────

class ClientResponse(BaseModel):
    """תגובת לקוח — פרטי זהות בלבד."""
    id: int
    full_name: str
    id_number: str
    id_number_type: Optional[IdNumberType] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address_street: Optional[str] = None
    address_building_number: Optional[str] = None
    address_apartment: Optional[str] = None
    address_city: Optional[str] = None
    address_zip_code: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

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
    deleted_at: datetime

    model_config = {"from_attributes": True}


class ClientConflictInfo(BaseModel):
    """
    מידע מלא על קונפליקטים לת.ז. נתונה.
    מוחזר כחלק מתגובת 409.
    """
    id_number: str
    active_clients: list[ActiveClientSummary]
    deleted_clients: list[DeletedClientSummary]
