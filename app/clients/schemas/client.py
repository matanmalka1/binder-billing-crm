from datetime import date
from typing import Literal, Optional, Any

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from app.utils.id_validation import validate_israeli_id_checksum
from app.clients.models.client import ClientStatus, ClientType


class ClientCreateRequest(BaseModel):
    full_name: str
    id_number: str
    client_type: ClientType
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    opened_at: date

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
        if not validate_israeli_id_checksum(self.id_number):
            raise ValueError("מספר זהות/ח.פ אינו תקין")
        return self
    
    
class ClientUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    notes: Optional[str] = None
    status: Optional[ClientStatus] = None
    client_type: Optional[ClientType] = None
    primary_binder_number: Optional[str] = None
    # Structured address fields
    address_street: Optional[str] = None
    address_building_number: Optional[str] = None
    address_apartment: Optional[str] = None
    address_city: Optional[str] = None
    address_zip_code: Optional[str] = None


class ClientResponse(BaseModel):
    id: int
    full_name: str
    id_number: str
    client_type: str
    status: str
    primary_binder_number: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None
    # Structured address fields
    address_street: Optional[str] = None
    address_building_number: Optional[str] = None
    address_apartment: Optional[str] = None
    address_city: Optional[str] = None
    address_zip_code: Optional[str] = None
    opened_at: date
    closed_at: Optional[date] = None
    available_actions: list[dict[str, Any]] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ClientListResponse(BaseModel):
    items: list[ClientResponse]
    page: int
    page_size: int
    total: int


class BulkClientActionRequest(BaseModel):
    client_ids: list[int] = Field(min_length=1)
    action: Literal["freeze", "close", "activate"]


class BulkClientFailedItem(BaseModel):
    id: int
    error: str


class BulkClientActionResponse(BaseModel):
    succeeded: list[int]
    failed: list[BulkClientFailedItem]