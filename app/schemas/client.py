from datetime import date
from typing import Optional

from pydantic import BaseModel


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


class ClientResponse(BaseModel):
    id: int
    full_name: str
    id_number: str
    client_type: str
    status: str
    phone: Optional[str] = None
    email: Optional[str] = None
    opened_at: date
    closed_at: Optional[date] = None

    model_config = {"from_attributes": True}


class ClientListResponse(BaseModel):
    items: list[ClientResponse]
    page: int
    page_size: int
    total: int