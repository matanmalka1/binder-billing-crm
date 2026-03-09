from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PermanentDocumentResponse(BaseModel):
    id: int
    client_id: int
    document_type: str
    storage_key: str
    tax_year: Optional[int] = None
    is_present: bool
    uploaded_by: int
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class PermanentDocumentListResponse(BaseModel):
    items: list[PermanentDocumentResponse]


class OperationalSignalsResponse(BaseModel):
    client_id: int
    missing_documents: list[str]