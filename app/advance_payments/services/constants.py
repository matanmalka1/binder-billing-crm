"""Advance payment domain constants."""

from decimal import Decimal

from app.config import config

ADVANCE_PAYMENT_VAT_RATE: Decimal = config.ADVANCE_PAYMENT_VAT_RATE
MONTHLY_PERIOD_MONTHS_COUNT = 1
BIMONTHLY_PERIOD_MONTHS_COUNT = 2
SUPPORTED_PERIOD_MONTH_COUNTS = frozenset(
    {MONTHLY_PERIOD_MONTHS_COUNT, BIMONTHLY_PERIOD_MONTHS_COUNT}
)
BIMONTHLY_START_MONTHS = (1, 3, 5, 7, 9, 11)


def get_period_start_months(period_months_count: int) -> list[int]:
    if period_months_count == BIMONTHLY_PERIOD_MONTHS_COUNT:
        return list(BIMONTHLY_START_MONTHS)
    return list(range(1, 13))
