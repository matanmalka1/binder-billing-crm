import math
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, field_validator

from app.correspondence.models.correspondence import CorrespondenceType
from app.core.api_types import ApiDateTime


def _validate_occurred_at(v: Optional[datetime]) -> Optional[datetime]:
    if v is None:
        return v
    now = datetime.now(timezone.utc)
    v_aware = v if v.tzinfo is not None else v.replace(tzinfo=timezone.utc)
    if v_aware > now:
        raise ValueError("תאריך ההתכתבות לא יכול להיות בעתיד")
    return v


class CorrespondenceCreateRequest(BaseModel):
    contact_id: Optional[int] = None
    correspondence_type: CorrespondenceType
    subject: str
    notes: Optional[str] = None
    occurred_at: ApiDateTime

    @field_validator("occurred_at")
    @classmethod
    def occurred_at_not_future(cls, v: datetime) -> datetime:
        return _validate_occurred_at(v)


class CorrespondenceUpdateRequest(BaseModel):
    contact_id: Optional[int] = None
    correspondence_type: Optional[CorrespondenceType] = None
    subject: Optional[str] = None
    notes: Optional[str] = None
    occurred_at: Optional[ApiDateTime] = None

    @field_validator("occurred_at")
    @classmethod
    def occurred_at_not_future(cls, v: Optional[datetime]) -> Optional[datetime]:
        return _validate_occurred_at(v)


class CorrespondenceResponse(BaseModel):
    id: int
    business_id: int
    contact_id: Optional[int] = None
    correspondence_type: CorrespondenceType
    subject: str
    notes: Optional[str] = None
    occurred_at: ApiDateTime
    created_by: int
    created_at: ApiDateTime

    model_config = {"from_attributes": True}


class CorrespondenceListResponse(BaseModel):
    items: list[CorrespondenceResponse]
    page: int
    page_size: int
    total: int
    total_pages: int

    @classmethod
    def build(
        cls,
        items: list[CorrespondenceResponse],
        page: int,
        page_size: int,
        total: int,
    ) -> "CorrespondenceListResponse":
        return cls(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=math.ceil(total / page_size) if page_size else 0,
        )
