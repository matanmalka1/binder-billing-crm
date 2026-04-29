"""
tax_rules — מקור האמת הרשמי לחוקי מס ישראל.

נקודת כניסה ראשית: registry.py
  from app.tax_rules.registry import get_obligations, get_financials, get_periodic_calendar, ...
"""
from .registry import (
    get_annual_calendar,
    get_annual_report_rule,
    get_btl_due_day,
    get_effective_periodic_date,
    get_financial,
    get_financials,
    get_ni_brackets,
    get_obligations,
    get_periodic_calendar,
    get_vat_deduction_rate,
    validate,
)
from .sources import SOURCES

TAX_RULES_VERSION = "2026.2"

__all__ = [
    "TAX_RULES_VERSION",
    "SOURCES",
    "get_annual_calendar",
    "get_annual_report_rule",
    "get_btl_due_day",
    "get_effective_periodic_date",
    "get_financial",
    "get_financials",
    "get_ni_brackets",
    "get_obligations",
    "get_periodic_calendar",
    "get_vat_deduction_rate",
    "validate",
]
