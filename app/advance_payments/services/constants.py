"""Advance payment domain constants."""

import datetime as _dt
import os
from decimal import Decimal

from app.common.integrations.tax_rules_financials import get_vat_rate_percent


def _resolve_vat_rate() -> Decimal:
    pct = get_vat_rate_percent(_dt.date.today().year)
    if pct is not None:
        return Decimal(str(pct)) / Decimal("100")
    return Decimal(os.getenv("ADVANCE_PAYMENT_VAT_RATE", "0.18"))


ADVANCE_PAYMENT_VAT_RATE: Decimal = _resolve_vat_rate()
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
