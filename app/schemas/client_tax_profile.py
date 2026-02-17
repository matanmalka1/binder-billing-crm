from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TaxProfileResponse(BaseModel):
    client_id: int
    vat_type: Optional[str] = None
    business_type: Optional[str] = None
    tax_year_start: Optional[int] = None
    accountant_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TaxProfileUpdateRequest(BaseModel):
    vat_type: Optional[str] = None
    business_type: Optional[str] = None
    tax_year_start: Optional[int] = None
    accountant_name: Optional[str] = None
