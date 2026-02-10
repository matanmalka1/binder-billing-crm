from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TimelineEvent(BaseModel):
    """Single timeline event."""
    
    event_type: str
    timestamp: datetime
    binder_id: Optional[int] = None
    charge_id: Optional[int] = None
    description: str
    metadata: dict = {}


class ClientTimelineResponse(BaseModel):
    """Client timeline response."""
    
    client_id: int
    events: list[TimelineEvent]
    page: int
    page_size: int
    total: int