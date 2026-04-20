from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field

from app.core.api_types import ApiDateTime


class TimelineEvent(BaseModel):
    """Single timeline event."""

    event_type: str
    timestamp: ApiDateTime
    binder_id: Optional[int] = None
    charge_id: Optional[int] = None
    description: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    actions: Optional[list[dict[str, Any]]] = Field(
        default=None, deprecated=True
    )  # deprecated — use available_actions
    available_actions: Optional[list[dict[str, Any]]] = None


class ClientTimelineResponse(BaseModel):
    """Client timeline response."""

    client_record_id: int
    events: list[TimelineEvent]
    page: int
    page_size: int
    total: int
