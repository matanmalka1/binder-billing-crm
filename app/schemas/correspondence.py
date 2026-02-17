from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CorrespondenceCreateRequest(BaseModel):
    contact_id: Optional[int] = None
    correspondence_type: str
    subject: str
    notes: Optional[str] = None
    occurred_at: datetime


class CorrespondenceResponse(BaseModel):
    id: int
    client_id: int
    contact_id: Optional[int] = None
    correspondence_type: str
    subject: str
    notes: Optional[str] = None
    occurred_at: datetime
    created_by: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CorrespondenceListResponse(BaseModel):
    items: list[CorrespondenceResponse]
