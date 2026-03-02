from datetime import date
from typing import Optional, Any

from pydantic import BaseModel, Field


class ClientCreateRequest(BaseModel):
    full_name: str
    id_number: str
    client_type: str
    phone: Optional[str] = None
    email: Optional[str] = None
    opened_at: date


class ClientUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    client_type: Optional[str] = None
    primary_binder_number: Optional[str] = None
    address: Optional[str] = None
    business_sector: Optional[str] = None


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
    address: Optional[str] = None
    business_sector: Optional[str] = None
    opened_at: date
    closed_at: Optional[date] = None
    available_actions: list[dict[str, Any]] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ClientListResponse(BaseModel):
    items: list[ClientResponse]
    page: int
    page_size: int
    total: int
