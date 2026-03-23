from datetime import datetime
from typing import Optional

from pydantic import BaseModel, HttpUrl

from app.core.api_types import ApiDateTime


class InvoiceAttachRequest(BaseModel):
    """צירוף חשבונית חיצונית לחיוב קיים."""
    charge_id: int
    provider: str
    external_invoice_id: str
    issued_at: ApiDateTime
    document_url: Optional[str] = None


class InvoiceResponse(BaseModel):
    id: int
    charge_id: int
    provider: str
    external_invoice_id: str
    document_url: Optional[str] = None
    issued_at: ApiDateTime
    created_at: ApiDateTime

    model_config = {"from_attributes": True}
