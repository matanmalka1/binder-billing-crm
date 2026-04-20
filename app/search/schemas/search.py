from typing import Optional

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """Single search result."""

    result_type: str  # "client" | "binder"
    client_id: int
    office_client_number: Optional[int] = None
    client_name: str
    id_number: Optional[str] = None
    client_status: Optional[str] = None
    binder_id: Optional[int] = None
    binder_number: Optional[str] = None


class DocumentSearchResult(BaseModel):
    """Single document search result."""

    id: int
    client_record_id: int
    office_client_number: Optional[int] = None
    business_id: int
    business_name: str
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
