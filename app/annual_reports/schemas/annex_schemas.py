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


class ScheduleGimmelData(BaseModel):
    """נספח ג — רווח הון מניירות ערך סחירים"""
    security_name: Optional[str] = None
    quantity: Optional[Decimal] = None
    purchase_price: Optional[Decimal] = None
    sale_price: Optional[Decimal] = None
    gain_loss: Optional[Decimal] = None


class ScheduleDaletData(BaseModel):
    """נספח ד — הכנסות מחו\"ל והמס ששולם שם"""
    country: Optional[str] = None
    income_type: Optional[str] = None
    gross_income: Optional[Decimal] = None
    foreign_tax_paid: Optional[Decimal] = None
    net_income: Optional[Decimal] = None


class Form150Data(BaseModel):
    """טופס 150 — החזקה בחבר בני אדם תושב חוץ."""
    foreign_entity_name: Optional[str] = None
    country: Optional[str] = None
    holding_percentage: Optional[Decimal] = None
    control_rights: Optional[str] = None


class Form1504Data(BaseModel):
    """טופס 1504 — דיווח שותף בשותפות."""
    partnership_name: Optional[str] = None
    partnership_id_number: Optional[str] = None
    share_percentage: Optional[Decimal] = None
    income_share: Optional[Decimal] = None


class Form6111Data(BaseModel):
    """טופס 6111 — קידוד דוחות כספיים."""
    turnover_amount: Optional[Decimal] = None
    accounting_method: Optional[str] = None
    bookkeeping_basis: Optional[str] = None


class Form1344Data(BaseModel):
    """טופס 1344 — דיווח על הפסדים רלוונטיים."""
    loss_type: Optional[str] = None
    originating_year: Optional[int] = None
    loss_amount: Optional[Decimal] = None
    utilized_amount: Optional[Decimal] = None


class Form1399Data(BaseModel):
    """טופס 1399 — הודעה על מכירת נכס ורווח הון."""
    asset_description: Optional[str] = None
    sale_date: Optional[str] = None
    proceeds_amount: Optional[Decimal] = None
    cost_amount: Optional[Decimal] = None
    capital_gain: Optional[Decimal] = None


class Form1350Data(BaseModel):
    """טופס 1350 — משיכות בעל מניות מהותי."""
    company_name: Optional[str] = None
    withdrawal_amount: Optional[Decimal] = None
    withdrawal_date: Optional[str] = None
    balance_at_year_end: Optional[Decimal] = None


class Form1327Data(BaseModel):
    """טופס 1327 — דוח נאמנות."""
    trust_name: Optional[str] = None
    trustee_name: Optional[str] = None
    israel_income: Optional[Decimal] = None
    foreign_income: Optional[Decimal] = None


class Form1342Data(BaseModel):
    """טופס 1342 — פירוט נכסים שנתבע בגינם פחת."""
    asset_description: Optional[str] = None
    asset_cost: Optional[Decimal] = None
    depreciation_rate: Optional[Decimal] = None


class Form1343Data(BaseModel):
    """טופס 1343 — ניכוי נוסף בשל פחת."""
    asset_description: Optional[str] = None
    qualifying_amount: Optional[Decimal] = None
    extra_deduction_amount: Optional[Decimal] = None


class Form1348Data(BaseModel):
    """טופס 1348 — הצהרת אי-תושבות ישראל."""
    foreign_residency_country: Optional[str] = None
    days_in_israel: Optional[int] = None
    tie_breaker_basis: Optional[str] = None


class Form858Data(BaseModel):
    """טופס 858 — יחידות השתתפות בשותפות נפט."""
    partnership_name: Optional[str] = None
    units_held: Optional[Decimal] = None
    income_share: Optional[Decimal] = None
    expense_share: Optional[Decimal] = None


SCHEDULE_VALIDATORS: dict[str, type[BaseModel]] = {
    "schedule_a": ScheduleAData,
    "schedule_b": ScheduleBData,
    "schedule_gimmel": ScheduleGimmelData,
    "schedule_dalet": ScheduleDaletData,
    "form_150": Form150Data,
    "form_1504": Form1504Data,
    "form_6111": Form6111Data,
    "form_1344": Form1344Data,
    "form_1399": Form1399Data,
    "form_1350": Form1350Data,
    "form_1327": Form1327Data,
    "form_1342": Form1342Data,
    "form_1343": Form1343Data,
    "form_1348": Form1348Data,
    "form_858": Form858Data,
}
