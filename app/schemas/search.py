from typing import Optional

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """Single search result."""

    result_type: str  # "client" | "binder"
    client_id: int
    client_name: str
    binder_id: Optional[int] = None
    binder_number: Optional[str] = None
    work_state: Optional[str] = None
    sla_state: Optional[str] = None
    signals: list[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    """Search results response."""

    results: list[SearchResult]
    page: int
    page_size: int
    total: int
