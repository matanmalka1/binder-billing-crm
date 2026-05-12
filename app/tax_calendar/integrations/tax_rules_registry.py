"""Adapter for tax_rules_config registry access used by tax calendar generation."""

from __future__ import annotations

import logging
from datetime import date

from app.common.enums import DeadlineRuleType

_log = logging.getLogger(__name__)

try:
    from tax_rules.registry import get_effective_periodic_date as _registry_periodic

    _REGISTRY_AVAILABLE = True
except Exception:
    _REGISTRY_AVAILABLE = False

_REGISTRY_COLUMN = "effective_vat_periodic_and_income_tax_advances"

# Only VAT and advance-payment periodic rules map to this registry column.
_REGISTRY_RULE_TYPES: frozenset[DeadlineRuleType] = frozenset(
    {
        DeadlineRuleType.VAT_MONTHLY,
        DeadlineRuleType.VAT_BIMONTHLY,
        DeadlineRuleType.ADVANCE_MONTHLY,
        DeadlineRuleType.ADVANCE_BIMONTHLY,
    }
)


def registry_periodic_calendar_available(year: int) -> bool:
    """True when the tax_rules registry has an official periodic calendar for year."""
    if not _REGISTRY_AVAILABLE:
        return False
    try:
        from tax_rules.registry import get_periodic_calendar as _get_periodic_calendar

        _get_periodic_calendar(year)
        return True
    except KeyError:
        return False


def missing_registry_years(start_year: int, end_year: int) -> list[int]:
    """Years in [start_year, end_year] that lack official periodic registry data."""
    return [
        y
        for y in range(start_year, end_year + 1)
        if not registry_periodic_calendar_available(y)
    ]


def get_registry_due_date(
    rule_type: DeadlineRuleType,
    period_year: int,
    period_month: int,
    offset_months: int,
) -> date | None:
    """Return official effective date from tax_rules_config or None.

    Calendar key = last month covered by the reporting period:
      monthly (offset=1):   same as period month.
      bimonthly (offset=2): period_month + 1.
    General: shift(period, max(offset - 1, 0)).
    Returns None when no registry data exists for the year (future/past years).
    Logs a warning when the registry call fails.
    """
    if not _REGISTRY_AVAILABLE or rule_type not in _REGISTRY_RULE_TYPES:
        return None
    cal_year, cal_month = _shift_month(
        period_year, period_month, max(offset_months - 1, 0)
    )
    period_key = f"{cal_year}-{cal_month:02d}"
    try:
        raw = _registry_periodic(cal_year, period_key, _REGISTRY_COLUMN)
        return date.fromisoformat(raw) if raw else None
    except Exception as exc:
        _log.warning(
            "tax_rules registry lookup failed — falling back to DeadlineRule. "
            "rule_type=%s period_key=%s column=%s error=%r",
            rule_type.value,
            period_key,
            _REGISTRY_COLUMN,
            exc,
        )
        return None


def _shift_month(year: int, month: int, offset_months: int) -> tuple[int, int]:
    total = (month - 1) + offset_months
    return year + total // 12, (total % 12) + 1
