from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PermanentDocumentResponse(BaseModel):
    id: int
    business_id: int
    document_type: str
    storage_key: str
    tax_year: Optional[int] = None
    is_present: bool
    uploaded_by: int
    uploaded_at: datetime
    version: int
    superseded_by: Optional[int] = None
    status: str
    annual_report_id: Optional[int] = None
    original_filename: Optional[str] = None
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    notes: Optional[str] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    is_deleted: bool

    model_config = {"from_attributes": True}


class PermanentDocumentListResponse(BaseModel):
    items: list[PermanentDocumentResponse]


class OperationalSignalsResponse(BaseModel):
    business_id: int
    missing_documents: list[str]


class DocumentVersionsResponse(BaseModel):
    items: list[PermanentDocumentResponse]


class RejectDocumentRequest(BaseModel):
    notes: str


class ApproveDocumentRequest(BaseModel):
    pass


class UpdateNotesRequest(BaseModel):
    notes: str