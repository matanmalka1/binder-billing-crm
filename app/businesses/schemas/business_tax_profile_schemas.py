from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.businesses.models.business_tax_profile import VatType


class BusinessTaxProfileResponse(BaseModel):
    business_id: int
    vat_type: Optional[VatType] = None
    vat_start_date: Optional[date] = None           # קיים במודל
    vat_exempt_ceiling: Optional[Decimal] = None    # קיים במודל
    accountant_name: Optional[str] = None
    advance_rate: Optional[Decimal] = None
    advance_rate_updated_at: Optional[date] = None  # קיים במודל
    fiscal_year_start_month: int = 1                # קיים במודל, ברירת מחדל 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class BusinessTaxProfileUpdateRequest(BaseModel):
    vat_type: Optional[VatType] = None              # enum — לא str חופשי
    vat_start_date: Optional[date] = None
    vat_exempt_ceiling: Optional[Decimal] = Field(None, ge=0)
    accountant_name: Optional[str] = None
    advance_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    advance_rate_updated_at: Optional[date] = None
    fiscal_year_start_month: Optional[int] = Field(None, ge=1, le=12)