from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

from app.authority_contact.models.authority_contact import ContactType


class AuthorityContactCreateRequest(BaseModel):
    contact_type: ContactType
    name: str
    office: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    notes: Optional[str] = None


class AuthorityContactUpdateRequest(BaseModel):
    contact_type: Optional[ContactType] = None
    name: Optional[str] = None
    office: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    notes: Optional[str] = None


class AuthorityContactResponse(BaseModel):
    id: int
    business_id: int
    contact_type: ContactType
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
    page: int
    page_size: int
    total: int
