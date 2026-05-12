"""Shared period/deadline helpers used across advance_payments, binders, and dashboard."""

from datetime import date

ADVANCE_PAYMENT_DUE_DAY = 15

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


def build_due_date(
    year: int,
    start_month: int,
    period_months_count: int,
    due_day: int = ADVANCE_PAYMENT_DUE_DAY,
) -> date:
    due_month = start_month + period_months_count
    due_year = year
    if due_month > 12:
        due_month -= 12
        due_year += 1
    return date(due_year, due_month, due_day)


def _shift_month(year: int, month: int, offset: int) -> tuple[int, int]:
    month_index = year * 12 + month - 1 + offset
    return month_index // 12, month_index % 12 + 1


def _period_key(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def monthly_vat_period(reference_date: date) -> tuple[str, str]:
    year, month = _shift_month(reference_date.year, reference_date.month, -1)
    return _period_key(year, month), f"{HEBREW_MONTHS[month - 1]} {year}"


def bimonthly_vat_period(reference_date: date) -> tuple[str, str]:
    year, month = _shift_month(reference_date.year, reference_date.month, -1)
    if month % 2:
        year, month = _shift_month(year, month, -1)
    start_year, start_month = _shift_month(year, month, -1)
    label = f"{HEBREW_MONTHS[start_month - 1]}-{HEBREW_MONTHS[month - 1]} {year}"
    if start_year != year:
        label = f"{HEBREW_MONTHS[start_month - 1]} {start_year}-{HEBREW_MONTHS[month - 1]} {year}"
    return _period_key(year, month), label


def bimonthly_advance_payment_period(reference_date: date) -> tuple[str, str]:
    year, end_month = _shift_month(reference_date.year, reference_date.month, -1)
    if end_month % 2:
        year, end_month = _shift_month(year, end_month, -1)
    start_year, start_month = _shift_month(year, end_month, -1)
    label = f"{HEBREW_MONTHS[start_month - 1]}-{HEBREW_MONTHS[end_month - 1]} {year}"
    if start_year != year:
        label = f"{HEBREW_MONTHS[start_month - 1]} {start_year}-{HEBREW_MONTHS[end_month - 1]} {year}"
    return _period_key(start_year, start_month), label
