from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class ReminderCreateRequest(BaseModel):
    """Request schema for creating a reminder."""
    
    client_id: int = Field(..., gt=0, description="Client ID")
    reminder_type: str = Field(
        ...,
        description="Type of reminder",
        pattern="^(TAX_DEADLINE_APPROACHING|BINDER_IDLE|UNPAID_CHARGE|CUSTOM)$",
    )
    target_date: date = Field(..., description="Target date for the event")
    days_before: int = Field(..., ge=0, description="Days before target to send reminder")
    message: str = Field(..., min_length=1, description="Reminder message")
    
    # Optional foreign keys
    binder_id: Optional[int] = Field(None, gt=0, description="Related binder ID")
    charge_id: Optional[int] = Field(None, gt=0, description="Related charge ID")
    tax_deadline_id: Optional[int] = Field(None, gt=0, description="Related tax deadline ID")


class ReminderResponse(BaseModel):
    """Response schema for a reminder."""
    
    id: int
    client_id: int
    reminder_type: str
    status: str
    target_date: date
    days_before: int
    send_on: date
    message: str
    created_at: datetime
    sent_at: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    binder_id: Optional[int] = None
    charge_id: Optional[int] = None
    tax_deadline_id: Optional[int] = None
    
    model_config = {"from_attributes": True}


class ReminderListResponse(BaseModel):
    """Response schema for list of reminders."""
    
    items: list[ReminderResponse]
    page: int
    page_size: int
    total: int