from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.businesses.models.business_tax_profile import VatType
from app.core.api_types import ApiDateTime, ApiDecimal


class BusinessTaxProfileResponse(BaseModel):
    business_id: int
    vat_type: Optional[VatType] = None
    # Resolved VAT display fields — set by service layer, not from ORM directly
    business_type_key: Optional[str] = None          # Business.business_type value
    client_vat_reporting_frequency: Optional[VatType] = None  # Client.vat_reporting_frequency
    vat_start_date: Optional[date] = None           # קיים במודל
    vat_exempt_ceiling: Optional[ApiDecimal] = None    # קיים במודל
    business_type: Optional[str] = None
    tax_year_start: Optional[int] = None
    accountant_name: Optional[str] = None
    advance_rate: Optional[ApiDecimal] = None
    advance_rate_updated_at: Optional[date] = None  # קיים במודל
    fiscal_year_start_month: int = 1                # קיים במודל, ברירת מחדל 1
    created_at: Optional[ApiDateTime] = None
    updated_at: Optional[ApiDateTime] = None

    model_config = {"from_attributes": True}


class BusinessTaxProfileUpdateRequest(BaseModel):
    vat_type: Optional[VatType] = None              # enum — לא str חופשי
    vat_start_date: Optional[date] = None
    vat_exempt_ceiling: Optional[ApiDecimal] = Field(None, ge=0)
    business_type: Optional[str] = None
    tax_year_start: Optional[int] = Field(None, ge=1900, le=2100)
    accountant_name: Optional[str] = None
    advance_rate: Optional[ApiDecimal] = Field(None, ge=0, le=100)
    advance_rate_updated_at: Optional[date] = None
    fiscal_year_start_month: Optional[int] = Field(None, ge=1, le=12)
