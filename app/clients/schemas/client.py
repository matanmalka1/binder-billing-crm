from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.clients.models.client import ClientStatus, IdNumberType
from app.common.enums import EntityType, VatType
from app.core.api_types import ApiDateTime, ApiDecimal
from app.utils.id_validation import validate_israeli_id_checksum


# ─── Requests ────────────────────────────────────────────────────────────────

class ClientCreateRequest(BaseModel):
    """
    יצירת לקוח חדש — פרטי זהות ופרופיל מס.
    שדות פעילות עסקית (business_name, opened_at וכו') נמצאים ב-BusinessCreateRequest.
    """
    full_name: str
    id_number: str
    id_number_type: IdNumberType = IdNumberType.INDIVIDUAL
    entity_type: Optional[EntityType] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address_street: Optional[str] = None
    address_building_number: Optional[str] = None
    address_apartment: Optional[str] = None
    address_city: Optional[str] = None
    address_zip_code: Optional[str] = None
    # ── Tax reporting ─────────────────────────────────────────────────────────
    vat_reporting_frequency: Optional[VatType] = None
    vat_exempt_ceiling: Optional[ApiDecimal] = Field(None, ge=0)
    advance_rate: Optional[ApiDecimal] = Field(None, ge=0, le=100)
    accountant_name: Optional[str] = None

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

        if self.id_number_type == IdNumberType.CORPORATION:
            if not validate_israeli_id_checksum(self.id_number):
                raise ValueError("מספר ח.פ אינו תקין")

        non_employee_types = {EntityType.OSEK_PATUR, EntityType.OSEK_MURSHE, EntityType.COMPANY_LTD}
        if self.entity_type in non_employee_types and self.vat_reporting_frequency is None:
            raise ValueError("יש לציין תדירות דיווח מע״מ עבור עוסק/חברה")

        return self


class ClientUpdateRequest(BaseModel):
    """עדכון פרטי זהות ופרופיל מס."""
    full_name: Optional[str] = None
    status: Optional[ClientStatus] = None
    entity_type: Optional[EntityType] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address_street: Optional[str] = None
    address_building_number: Optional[str] = None
    address_apartment: Optional[str] = None
    address_city: Optional[str] = None
    address_zip_code: Optional[str] = None
    # ── Tax reporting ─────────────────────────────────────────────────────────
    vat_reporting_frequency: Optional[VatType] = None
    vat_exempt_ceiling: Optional[ApiDecimal] = Field(None, ge=0)
    advance_rate: Optional[ApiDecimal] = Field(None, ge=0, le=100)
    advance_rate_updated_at: Optional[date] = None
    accountant_name: Optional[str] = None


# ─── Responses ────────────────────────────────────────────────────────────────

class ClientResponse(BaseModel):
    """תגובת לקוח — פרטי זהות ופרופיל מס."""
    id: int
    full_name: str
    id_number: str
    id_number_type: Optional[IdNumberType] = None
    entity_type: Optional[EntityType] = None
    status: ClientStatus = ClientStatus.ACTIVE
    phone: Optional[str] = None
    email: Optional[str] = None
    address_street: Optional[str] = None
    address_building_number: Optional[str] = None
    address_apartment: Optional[str] = None
    address_city: Optional[str] = None
    address_zip_code: Optional[str] = None
    notes: Optional[str] = None
    # ── Tax reporting ─────────────────────────────────────────────────────────
    vat_reporting_frequency: Optional[VatType] = None
    vat_exempt_ceiling: Optional[ApiDecimal] = None
    advance_rate: Optional[ApiDecimal] = None
    advance_rate_updated_at: Optional[date] = None
    accountant_name: Optional[str] = None
    created_at: Optional[ApiDateTime] = None
    updated_at: Optional[ApiDateTime] = None
    # ── Enriched field (set by API layer, not stored on Client) ───────────────
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
