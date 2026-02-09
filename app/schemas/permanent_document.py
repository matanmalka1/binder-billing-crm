from datetime import datetime

from pydantic import BaseModel


class PermanentDocumentResponse(BaseModel):
    id: int
    client_id: int
    document_type: str
    storage_key: str
    is_present: bool
    uploaded_by: int
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class PermanentDocumentListResponse(BaseModel):
    items: list[PermanentDocumentResponse]


class OperationalSignalsResponse(BaseModel):
    client_id: int
    missing_documents: list[str]
    binders_nearing_sla: list[dict]
    binders_overdue: list[dict]