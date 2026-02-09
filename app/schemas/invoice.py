from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class InvoiceAttachRequest(BaseModel):
    provider: str
    external_invoice_id: str
    issued_at: datetime
    document_url: Optional[str] = None


class InvoiceResponse(BaseModel):
    id: int
    charge_id: int
    provider: str
    external_invoice_id: str
    document_url: Optional[str] = None
    issued_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}