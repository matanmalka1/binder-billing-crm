from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CorrespondenceCreateRequest(BaseModel):
    contact_id: Optional[int] = None
    correspondence_type: str
    subject: str
    notes: Optional[str] = None
    occurred_at: datetime


class CorrespondenceUpdateRequest(BaseModel):
    contact_id: Optional[int] = None
    correspondence_type: Optional[str] = None
    subject: Optional[str] = None
    notes: Optional[str] = None
    occurred_at: Optional[datetime] = None


class CorrespondenceResponse(BaseModel):
    id: int
    business_id: int
    contact_id: Optional[int] = None
    correspondence_type: str
    subject: str
    notes: Optional[str] = None
    occurred_at: datetime
    created_by: int
    created_at: Optional[datetime] = None  # nullable — older seeded rows may lack this

    model_config = {"from_attributes": True}


class CorrespondenceListResponse(BaseModel):
    items: list[CorrespondenceResponse]
    page: int
    page_size: int
    total: int