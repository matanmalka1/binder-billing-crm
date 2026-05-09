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


def shift_month(year: int, month: int, offset: int) -> tuple[int, int]:
    month_index = year * 12 + month - 1 + offset
    return month_index // 12, month_index % 12 + 1


def period_key(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def monthly_vat_period(reference_date: date) -> tuple[str, str]:
    year, month = shift_month(reference_date.year, reference_date.month, -1)
    return period_key(year, month), f"{HEBREW_MONTHS[month - 1]} {year}"


def bimonthly_vat_period(reference_date: date) -> tuple[str, str]:
    year, month = shift_month(reference_date.year, reference_date.month, -1)
    if month % 2:
        year, month = shift_month(year, month, -1)
    start_year, start_month = shift_month(year, month, -1)
    label = f"{HEBREW_MONTHS[start_month - 1]}-{HEBREW_MONTHS[month - 1]} {year}"
    if start_year != year:
        label = f"{HEBREW_MONTHS[start_month - 1]} {start_year}-{HEBREW_MONTHS[month - 1]} {year}"
    return period_key(year, month), label


def bimonthly_advance_payment_period(reference_date: date) -> tuple[str, str]:
    year, end_month = shift_month(reference_date.year, reference_date.month, -1)
    if end_month % 2:
        year, end_month = shift_month(year, end_month, -1)
    start_year, start_month = shift_month(year, end_month, -1)
    label = f"{HEBREW_MONTHS[start_month - 1]}-{HEBREW_MONTHS[end_month - 1]} {year}"
    if start_year != year:
        label = f"{HEBREW_MONTHS[start_month - 1]} {start_year}-{HEBREW_MONTHS[end_month - 1]} {year}"
    return period_key(start_year, start_month), label


def vat_deadline_for_period(period: str, deadline_day: int) -> date:
    """Filing deadline for a VAT period string (YYYY-MM).

    The statutory deadline is deadline_day of the month following the period month.
    Works for both monthly and bimonthly periods (bimonthly period key = end month).
    """
    year, month = (int(x) for x in period.split("-", 1))
    if month == 12:
        return date(year + 1, 1, deadline_day)
    return date(year, month + 1, deadline_day)
