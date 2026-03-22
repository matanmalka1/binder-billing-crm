from typing import Optional

from pydantic import BaseModel, Field

from app.businesses.models.business import BusinessStatus


class SearchResult(BaseModel):
    """Single search result."""

    result_type: str  # "client" | "binder"
    business_id: int
    client_name: str
    client_status: Optional[BusinessStatus] = None
    binder_id: Optional[int] = None
    binder_number: Optional[str] = None
    work_state: Optional[str] = None
    signals: list[str] = Field(default_factory=list)


class DocumentSearchResult(BaseModel):
    """Single document search result."""

    id: int
    business_id: int
    client_name: str
    document_type: str
    original_filename: Optional[str] = None
    tax_year: Optional[int] = None
    status: str


class SearchResponse(BaseModel):
    """Search results response."""

    results: list[SearchResult]
    documents: list[DocumentSearchResult] = Field(default_factory=list)
    page: int
    page_size: int
    total: int
