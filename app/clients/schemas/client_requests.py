from datetime import date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.businesses.schemas.business_schemas import ClientBusinessCreateRequest
from app.clients.enums import ClientStatus
from app.clients.schemas.create_validation import (
    validate_create_entity_rules,
    validate_preview_entity_rules,
    validate_update_entity_rules,
)
from app.common.enums import EntityType, IdNumberType, VatType
from app.core.api_types import ApiDecimal

CREATE_CLIENT_REQUIRED_LABELS = {
    "full_name": "שם מלא",
    "phone": "טלפון",
    "address_street": "רחוב",
    "address_building_number": "מספר בניין",
    "address_city": "עיר",
}


class ClientCreateRequest(BaseModel):
    full_name: str
    id_number: str
    id_number_type: Optional[IdNumberType] = None
    entity_type: Optional[EntityType] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address_street: Optional[str] = None
    address_building_number: Optional[str] = None
    address_apartment: Optional[str] = None
    address_city: Optional[str] = None
    address_zip_code: Optional[str] = None
    vat_reporting_frequency: Optional[VatType] = None
    vat_exempt_ceiling: Optional[ApiDecimal] = Field(None, ge=0)
    advance_rate: Optional[ApiDecimal] = Field(None, ge=0, le=100)
    accountant_id: Optional[int] = None

    @field_validator("id_number")
    @classmethod
    def normalize_id_number(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("יש להזין מספר מזהה")
        return normalized

    @model_validator(mode="after")
    def validate_create_rules(self) -> "ClientCreateRequest":
        validate_create_entity_rules(
            entity_type=self.entity_type,
            id_number=self.id_number,
            provided_id_number_type=self.id_number_type,
            id_number_type_was_set="id_number_type" in self.model_fields_set,
            vat_reporting_frequency=self.vat_reporting_frequency,
            vat_reporting_frequency_was_set="vat_reporting_frequency" in self.model_fields_set,
            vat_exempt_ceiling_was_set="vat_exempt_ceiling" in self.model_fields_set,
        )
        return self


class ClientUpdateRequest(BaseModel):
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
    vat_reporting_frequency: Optional[VatType] = None
    vat_exempt_ceiling: Optional[ApiDecimal] = Field(None, ge=0)
    advance_rate: Optional[ApiDecimal] = Field(None, ge=0, le=100)
    advance_rate_updated_at: Optional[date] = None
    accountant_id: Optional[int] = None

    @model_validator(mode="after")
    def validate_update_rules(self) -> "ClientUpdateRequest":
        validate_update_entity_rules(
            vat_exempt_ceiling_was_set="vat_exempt_ceiling" in self.model_fields_set,
        )
        return self


class CreateClientRequest(BaseModel):
    client: ClientCreateRequest
    business: ClientBusinessCreateRequest

    @model_validator(mode="after")
    def require_full_create_payload(self) -> "CreateClientRequest":
        required_values = (
            ("full_name", self.client.full_name),
            ("phone", self.client.phone),
            ("address_street", self.client.address_street),
            ("address_building_number", self.client.address_building_number),
            ("address_city", self.client.address_city),
        )
        for field_name, value in required_values:
            if value is None or (isinstance(value, str) and not value.strip()):
                raise ValueError(f"יש להזין {CREATE_CLIENT_REQUIRED_LABELS[field_name]}")
        if self.client.entity_type is None:
            raise ValueError("יש לבחור סוג ישות")
        if self.client.email is None:
            raise ValueError("יש להזין כתובת אימייל")
        return self


class ClientImpactPreviewClientRequest(BaseModel):
    entity_type: EntityType
    vat_reporting_frequency: Optional[VatType] = None
    advance_rate: Optional[ApiDecimal] = Field(None, ge=0, le=100)

    @model_validator(mode="after")
    def validate_preview_rules(self) -> "ClientImpactPreviewClientRequest":
        validate_preview_entity_rules(
            entity_type=self.entity_type,
            vat_reporting_frequency=self.vat_reporting_frequency,
            vat_reporting_frequency_was_set="vat_reporting_frequency" in self.model_fields_set,
        )
        return self


class ClientImpactPreviewRequest(BaseModel):
    client: ClientImpactPreviewClientRequest
