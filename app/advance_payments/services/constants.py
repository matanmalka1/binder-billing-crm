"""Advance payment domain constants and period helpers."""

from datetime import date
from decimal import Decimal

from app.config import config

ADVANCE_PAYMENT_VAT_RATE: Decimal = config.ADVANCE_PAYMENT_VAT_RATE
MONTHLY_PERIOD_MONTHS_COUNT = 1
BIMONTHLY_PERIOD_MONTHS_COUNT = 2
SUPPORTED_PERIOD_MONTH_COUNTS = frozenset(
    {MONTHLY_PERIOD_MONTHS_COUNT, BIMONTHLY_PERIOD_MONTHS_COUNT}
)
BIMONTHLY_START_MONTHS = (1, 3, 5, 7, 9, 11)
ADVANCE_PAYMENT_DUE_DAY = 15


def parse_period_month(period: str) -> int:
    return int(period.split("-")[1])


def parse_period_year(period: str) -> int:
    return int(period.split("-")[0])


def get_period_start_months(period_months_count: int) -> list[int]:
    if period_months_count == BIMONTHLY_PERIOD_MONTHS_COUNT:
        return list(BIMONTHLY_START_MONTHS)
    return list(range(1, 13))


def build_due_date(year: int, start_month: int, period_months_count: int) -> date:
    due_month = start_month + period_months_count
    due_year = year
    if due_month > 12:
        due_month -= 12
        due_year += 1
    return date(due_year, due_month, ADVANCE_PAYMENT_DUE_DAY)
