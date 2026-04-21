from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.clients.enums import ClientStatus
from app.common.enums import EntityType, IdNumberType, VatType
from app.core.api_types import ApiDateTime, ApiDecimal
from app.utils.id_validation import validate_israeli_id_checksum
from app.businesses.schemas.business_schemas import BusinessCreateRequest, BusinessResponse
from app.clients.schemas.impact import ClientCreationImpactResponse

CREATE_CLIENT_REQUIRED_LABELS = {
    "full_name": "שם מלא",
    "phone": "טלפון",
    "address_street": "רחוב",
    "address_building_number": "מספר בניין",
    "address_apartment": "דירה",
    "address_city": "עיר",
    "address_zip_code": "מיקוד",
    "accountant_name": "רואה חשבון מלווה",
}


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


class CreateClientRequest(BaseModel):
    """יצירת לקוח ועסק ראשון."""
    client: ClientCreateRequest
    business: BusinessCreateRequest

    @model_validator(mode="after")
    def require_full_create_payload(self) -> "CreateClientRequest":
        required_client_strings = (
            ("full_name", self.client.full_name),
            ("phone", self.client.phone),
            ("address_street", self.client.address_street),
            ("address_building_number", self.client.address_building_number),
            ("address_apartment", self.client.address_apartment),
            ("address_city", self.client.address_city),
            ("address_zip_code", self.client.address_zip_code),
            ("accountant_name", self.client.accountant_name),
        )
        for field_name, value in required_client_strings:
            if value is None or not value.strip():
                raise ValueError(f"יש להזין {CREATE_CLIENT_REQUIRED_LABELS[field_name]}")

        if self.client.entity_type is None:
            raise ValueError("יש לבחור סוג ישות")
        if self.client.email is None:
            raise ValueError("יש להזין כתובת אימייל")
        if self.client.vat_reporting_frequency is None:
            raise ValueError("יש לציין תדירות דיווח מע״מ")
        if self.client.advance_rate is None:
            raise ValueError("יש להזין אחוז מקדמה")
        if self.business.opened_at is None:
            raise ValueError("יש להזין תאריך פתיחת עסק")
        if self.client.entity_type == EntityType.OSEK_PATUR and self.client.vat_exempt_ceiling is None:
            raise ValueError("יש להזין תקרת פטור מע״מ")

        return self


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
    office_client_number: Optional[int] = None
    notes: Optional[str] = None
    # ── Tax reporting ─────────────────────────────────────────────────────────
    vat_reporting_frequency: Optional[VatType] = None
    vat_exempt_ceiling: Optional[ApiDecimal] = None
    advance_rate: Optional[ApiDecimal] = None
    advance_rate_updated_at: Optional[date] = None
    accountant_name: Optional[str] = None
    created_at: Optional[ApiDateTime] = None
    updated_at: Optional[ApiDateTime] = None
    # ── Enriched field (set by API layer, not stored on ClientRecord) ─────────
    active_binder_number: Optional[str] = None

    model_config = {"from_attributes": True}


class ClientListStats(BaseModel):
    active: int = 0
    frozen: int = 0
    closed: int = 0


class ClientListResponse(BaseModel):
    items: list[ClientResponse]
    page: int
    page_size: int
    total: int
    stats: ClientListStats


class CreateClientResponse(BaseModel):
    client_record_id: int
    client: ClientResponse
    business: BusinessResponse
    impact: ClientCreationImpactResponse


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
