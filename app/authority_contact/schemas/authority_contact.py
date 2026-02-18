from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AuthorityContactCreateRequest(BaseModel):
    contact_type: str
    name: str
    office: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None


class AuthorityContactUpdateRequest(BaseModel):
    contact_type: Optional[str] = None
    name: Optional[str] = None
    office: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None


class AuthorityContactResponse(BaseModel):
    id: int
    client_id: int
    contact_type: str
    name: str
    office: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AuthorityContactListResponse(BaseModel):
    items: list[AuthorityContactResponse]