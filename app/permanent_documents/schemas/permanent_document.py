from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.permanent_documents.models.permanent_document import (
    DocumentScope,
    DocumentStatus,
    DocumentType,
)


class PermanentDocumentResponse(BaseModel):
    id: int
    client_id: int                         
    business_id: Optional[int] = None       # nullable — CLIENT scope
    scope: DocumentScope                   
    document_type: DocumentType            
    storage_key: str
    original_filename: Optional[str] = None
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    tax_year: Optional[int] = None
    is_present: bool
    is_deleted: bool
    status: DocumentStatus                 
    version: int
    superseded_by: Optional[int] = None
    annual_report_id: Optional[int] = None
    notes: Optional[str] = None
    uploaded_by: int
    uploaded_at: datetime
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    rejected_by: Optional[int] = None      
    rejected_at: Optional[datetime] = None  

    model_config = {"from_attributes": True}


class PermanentDocumentListResponse(BaseModel):
    items: list[PermanentDocumentResponse]


class DocumentVersionsResponse(BaseModel):
    items: list[PermanentDocumentResponse]


class OperationalSignalsResponse(BaseModel):
    business_id: int
    missing_documents: list[DocumentType]   


class RejectDocumentRequest(BaseModel):
    notes: str


class UpdateNotesRequest(BaseModel):
    notes: str