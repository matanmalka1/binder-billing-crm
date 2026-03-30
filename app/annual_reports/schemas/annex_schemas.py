"""Per-schedule Pydantic validators for annual report annex data.

Each schedule maps to a Pydantic model that validates the `data` JSON field
stored in AnnualReportAnnexData. Validators are intentionally permissive — all
fields are optional so existing data is never rejected during incremental rollout.

SCHEDULE_VALIDATORS is the single lookup used by annex_service.py.
If a schedule has no validator defined, the data dict passes through unchanged.
"""

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class ScheduleAData(BaseModel):
    """נספח א — חישוב הכנסה מעסק"""
    gross_income: Optional[Decimal] = None
    cost_of_goods: Optional[Decimal] = None
    gross_profit: Optional[Decimal] = None
    operating_expenses: Optional[Decimal] = None
    net_income: Optional[Decimal] = None


class ScheduleBData(BaseModel):
    """נספח ב — הכנסות מדמי שכירות"""
    property_address: Optional[str] = None
    rental_income: Optional[Decimal] = None
    depreciation_claimed: Optional[Decimal] = None
    maintenance_expenses: Optional[Decimal] = None
    net_rental_income: Optional[Decimal] = None


class ScheduleBetData(BaseModel):
    """נספח ב' — רווחי הון ממכירת נכסים"""
    asset_description: Optional[str] = None
    purchase_date: Optional[str] = None
    sale_date: Optional[str] = None
    purchase_price: Optional[Decimal] = None
    sale_price: Optional[Decimal] = None
    capital_gain: Optional[Decimal] = None
    tax_rate: Optional[Decimal] = None


class ScheduleGimmelData(BaseModel):
    """נספח ג — הכנסות מחו\"ל"""
    country: Optional[str] = None
    income_type: Optional[str] = None
    gross_income: Optional[Decimal] = None
    foreign_tax_paid: Optional[Decimal] = None
    net_income: Optional[Decimal] = None


class ScheduleDaletData(BaseModel):
    """נספח ד — פחת"""
    asset_description: Optional[str] = None
    asset_cost: Optional[Decimal] = None
    depreciation_rate: Optional[Decimal] = None
    accumulated_depreciation: Optional[Decimal] = None
    annual_depreciation: Optional[Decimal] = None
    book_value: Optional[Decimal] = None


class ScheduleHehData(BaseModel):
    """נספח ה — שכר דירה פטור ממס"""
    property_address: Optional[str] = None
    rental_income: Optional[Decimal] = None
    exempt_amount: Optional[Decimal] = None
    taxable_amount: Optional[Decimal] = None


class ScheduleVavData(BaseModel):
    """נספח ו — מכירת ניירות ערך"""
    security_name: Optional[str] = None
    quantity: Optional[Decimal] = None
    purchase_price: Optional[Decimal] = None
    sale_price: Optional[Decimal] = None
    gain_loss: Optional[Decimal] = None


class Annex15Data(BaseModel):
    """נספח 15 — הכנסות מחו\"ל מפורט"""
    country: Optional[str] = None
    income_description: Optional[str] = None
    gross_amount: Optional[Decimal] = None
    withholding_tax: Optional[Decimal] = None
    treaty_rate: Optional[Decimal] = None


class Annex867Data(BaseModel):
    """נספח 867 — אישור בנקאי"""
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    interest_income: Optional[Decimal] = None
    dividend_income: Optional[Decimal] = None
    withholding_tax: Optional[Decimal] = None


SCHEDULE_VALIDATORS: dict[str, type[BaseModel]] = {
    "schedule_a": ScheduleAData,
    "schedule_b": ScheduleBData,
    "schedule_bet": ScheduleBetData,
    "schedule_gimmel": ScheduleGimmelData,
    "schedule_dalet": ScheduleDaletData,
    "schedule_heh": ScheduleHehData,
    "schedule_vav": ScheduleVavData,
    "annex_15": Annex15Data,
    "annex_867": Annex867Data,
}
