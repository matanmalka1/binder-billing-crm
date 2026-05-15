"""Shared period/deadline helpers used across advance_payments, binders, and dashboard."""

from datetime import date

HEBREW_MONTHS = (
    "ינואר",
    "פברואר",
    "מרץ",
    "אפריל",
    "מאי",
    "יוני",
    "יולי",
    "אוגוסט",
    "ספטמבר",
    "אוקטובר",
    "נובמבר",
    "דצמבר",
)


def parse_period_year(period: str) -> int:
    return int(period.split("-")[0])


def parse_period_month(period: str) -> int:
    return int(period.split("-")[1])


def _shift_month(year: int, month: int, offset: int) -> tuple[int, int]:
    month_index = year * 12 + month - 1 + offset
    return month_index // 12, month_index % 12 + 1


def _period_key(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def monthly_vat_period(reference_date: date) -> tuple[str, str]:
    year, month = _shift_month(reference_date.year, reference_date.month, -1)
    return _period_key(year, month), f"{HEBREW_MONTHS[month - 1]} {year}"


def bimonthly_vat_period(reference_date: date) -> tuple[str, str]:
    year, end_month = _shift_month(reference_date.year, reference_date.month, -1)
    if end_month % 2:
        year, end_month = _shift_month(year, end_month, -1)
    start_year, start_month = _shift_month(year, end_month, -1)
    label = f"{HEBREW_MONTHS[start_month - 1]}-{HEBREW_MONTHS[end_month - 1]} {year}"
    if start_year != year:
        label = f"{HEBREW_MONTHS[start_month - 1]} {start_year}-{HEBREW_MONTHS[end_month - 1]} {year}"
    return _period_key(start_year, start_month), label


def bimonthly_advance_payment_period(reference_date: date) -> tuple[str, str]:
    year, end_month = _shift_month(reference_date.year, reference_date.month, -1)
    if end_month % 2:
        year, end_month = _shift_month(year, end_month, -1)
    start_year, start_month = _shift_month(year, end_month, -1)
    label = f"{HEBREW_MONTHS[start_month - 1]}-{HEBREW_MONTHS[end_month - 1]} {year}"
    if start_year != year:
        label = f"{HEBREW_MONTHS[start_month - 1]} {start_year}-{HEBREW_MONTHS[end_month - 1]} {year}"
    return _period_key(start_year, start_month), label
