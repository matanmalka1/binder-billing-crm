from datetime import date
from typing import Optional

from pydantic import BaseModel


class BinderReceiveRequest(BaseModel):
    client_id: int
    binder_number: str
    received_at: date
    received_by: int
    notes: Optional[str] = None


class BinderReturnRequest(BaseModel):
    pickup_person_name: str
    returned_by: int


class BinderResponse(BaseModel):
    id: int
    client_id: int
    binder_number: str
    status: str
    received_at: date
    expected_return_at: date
    returned_at: Optional[date] = None
    pickup_person_name: Optional[str] = None
    days_in_office: Optional[int] = None

    model_config = {"from_attributes": True}


class BinderListResponse(BaseModel):
    items: list[BinderResponse]