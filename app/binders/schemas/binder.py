from datetime import date, datetime
from typing import Optional, Any

from pydantic import BaseModel, Field

from app.binders.models.binder import BinderType


class BinderReceiveRequest(BaseModel):
    client_id: int
    binder_number: str
    binder_type: BinderType
    received_at: date
    received_by: int
    notes: Optional[str] = None


class BinderReturnRequest(BaseModel):
    pickup_person_name: Optional[str] = None
    returned_by: Optional[int] = None


class BinderResponse(BaseModel):
    id: int
    client_id: int
    client_name: Optional[str] = None
    binder_number: str
    binder_type: BinderType
    status: str
    received_at: date
    returned_at: Optional[date] = None
    pickup_person_name: Optional[str] = None
    days_in_office: Optional[int] = None
    work_state: Optional[str] = None
    signals: Optional[list[str]] = None
    available_actions: list[dict[str, Any]] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class BinderListResponse(BaseModel):
    items: list[BinderResponse]
    page: int
    page_size: int
    total: int


class BinderIntakeResponse(BaseModel):
    id: int
    binder_id: int
    received_at: date
    received_by: int
    received_by_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class BinderIntakeListResponse(BaseModel):
    binder_id: int
    intakes: list[BinderIntakeResponse]


class BinderReceiveResult(BaseModel):
    binder: BinderResponse
    intake: BinderIntakeResponse
    is_new_binder: bool
