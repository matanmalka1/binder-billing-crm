from datetime import date

from app.vat_reports.services.constants import VAT_STATUTORY_DEADLINE_DAY as _FALLBACK_DUE_DAY

try:
    from tax_rules import get_effective_periodic_date as _get_periodic_date

    _PERIODIC_CALENDAR_COLUMN = "effective_vat_periodic_and_income_tax_advances"
    _PERIODIC_CALENDAR_AVAILABLE = True
except ImportError:
    _PERIODIC_CALENDAR_AVAILABLE = False


def periodic_due_date(filing_year: int, filing_month: int, calendar_period: str) -> date:
    if _PERIODIC_CALENDAR_AVAILABLE:
        try:
            raw = _get_periodic_date(filing_year, calendar_period, _PERIODIC_CALENDAR_COLUMN)
        except KeyError:
            raw = None
        if raw:
            return date.fromisoformat(raw)
    return date(filing_year, filing_month, _FALLBACK_DUE_DAY)
