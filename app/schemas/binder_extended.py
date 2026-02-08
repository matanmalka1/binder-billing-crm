from datetime import date
from typing import Optional

from pydantic import BaseModel


class BinderDetailResponse(BaseModel):
    """Binder response with derived SLA fields."""
    
    id: int
    client_id: int
    binder_number: str
    status: str
    received_at: date
    expected_return_at: date
    returned_at: Optional[date] = None
    pickup_person_name: Optional[str] = None
    is_overdue: bool
    days_overdue: int

    model_config = {"from_attributes": True}


class BinderListResponseExtended(BaseModel):
    """Paginated binder list response."""
    
    items: list[BinderDetailResponse]
    page: int
    page_size: int
    total: int


class BinderHistoryEntry(BaseModel):
    """Single binder status log entry."""
    
    old_status: str
    new_status: str
    changed_by: int
    changed_at: str
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class BinderHistoryResponse(BaseModel):
    """Binder audit history response."""
    
    binder_id: int
    history: list[BinderHistoryEntry]
