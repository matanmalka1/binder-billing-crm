"""TaxCalendarEntry generation — calendar population.

Populates regulatory calendar entries shared across all clients. Idempotent:
re-running for the same year is a no-op. Does NOT modify business objects.

Due-date computation (priority order):
1. Official effective date from tax_rules_config registry
   (column: effective_vat_periodic_and_income_tax_advances).
   Covers VAT + advance payment periodic obligations, including holiday shifts.
   This is the STATUTORY effective date (15th shifted for holidays/weekends).
   It does NOT include the +4-day online filing extension — that is applied by
   the VAT serializer layer for online-submission clients only.
2. DeadlineRule base: (period start + offset_months) on due_day_of_month.
   Used when registry has no data for the year (e.g. future/past years).
- Annual entry:   due_date = (tax_year + 1 + offset_months) on due_day_of_month.
- Per-client overrides (extended/custom annual deadlines) live on AnnualReport.
- Registry lookup is restricted to VAT and advance-payment rule types only.
"""

from __future__ import annotations

import calendar
import logging
from datetime import date

from sqlalchemy.orm import Session

from app.common.enums import DeadlineRuleType, ObligationType
from app.tax_calendar.models.deadline_rule import DeadlineRule
from app.tax_calendar.models.tax_calendar_entry import TaxCalendarEntry

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


class MissingDeadlineRuleError(LookupError):
    """No active DeadlineRule covers the requested rule_type/year."""


_PERIODIC_PLAN: list[tuple[ObligationType, DeadlineRuleType, list[int], int]] = [
    (ObligationType.VAT, DeadlineRuleType.VAT_MONTHLY, list(range(1, 13)), 1),
    (ObligationType.VAT, DeadlineRuleType.VAT_BIMONTHLY, [1, 3, 5, 7, 9, 11], 2),
    (
        ObligationType.ADVANCE_PAYMENT,
        DeadlineRuleType.ADVANCE_MONTHLY,
        list(range(1, 13)),
        1,
    ),
    (
        ObligationType.ADVANCE_PAYMENT,
        DeadlineRuleType.ADVANCE_BIMONTHLY,
        [1, 3, 5, 7, 9, 11],
        2,
    ),
]

_RULE_KEY: dict[DeadlineRuleType, str] = {
    DeadlineRuleType.VAT_MONTHLY: "vat_monthly",
    DeadlineRuleType.VAT_BIMONTHLY: "vat_bimonthly",
    DeadlineRuleType.ADVANCE_MONTHLY: "advance_monthly",
    DeadlineRuleType.ADVANCE_BIMONTHLY: "advance_bimonthly",
}


def _shift_month(year: int, month: int, offset_months: int) -> tuple[int, int]:
    total = (month - 1) + offset_months
    return year + total // 12, (total % 12) + 1


def _clamp_day(year: int, month: int, day: int) -> int:
    return min(day, calendar.monthrange(year, month)[1])


def _registry_due_date(
    rule_type: DeadlineRuleType,
    period_year: int,
    period_month: int,
    offset_months: int,
) -> date | None:
    """Return official effective date from tax_rules_config or None.

    Only called for rule types in _REGISTRY_RULE_TYPES.
    Calendar key = last month covered by the reporting period:
      monthly (offset=1):   same as period month.
      bimonthly (offset=2): period_month + 1.
    General: shift(period, max(offset - 1, 0)).
    Returns None when no registry data exists for the year (future/past years).
    Logs a warning — does not silently swallow — when the registry call fails.
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


def periodic_due_date(rule: DeadlineRule, period_year: int, period_month: int) -> date:
    due_year, due_month = _shift_month(period_year, period_month, rule.offset_months)
    base = date(
        due_year, due_month, _clamp_day(due_year, due_month, rule.due_day_of_month)
    )
    rule_type = DeadlineRuleType(rule.rule_type)
    return (
        _registry_due_date(rule_type, period_year, period_month, rule.offset_months)
        or base
    )


def annual_due_date(rule: DeadlineRule, tax_year: int) -> date:
    year, month = _shift_month(tax_year + 1, 1, rule.offset_months)
    return date(year, month, _clamp_day(year, month, rule.due_day_of_month))


def _resolve_rule(
    db: Session,
    *,
    rule_type: DeadlineRuleType,
    on_date: date,
) -> DeadlineRule:
    rule = (
        db.query(DeadlineRule)
        .filter(DeadlineRule.rule_type == rule_type.value)
        .filter(DeadlineRule.effective_from <= on_date)
        .filter(
            (DeadlineRule.effective_to.is_(None))
            | (DeadlineRule.effective_to >= on_date)
        )
        .order_by(DeadlineRule.effective_from.desc())
        .first()
    )
    if rule is None:
        raise MissingDeadlineRuleError(
            f"No active DeadlineRule of type '{rule_type.value}' covering "
            f"{on_date}. Seed the rule before generating tax calendar entries."
        )
    return rule


def get_or_create_entry(
    db: Session,
    *,
    obligation_type: ObligationType,
    period: str | None,
    period_months_count: int | None,
    tax_year: int,
    deadline_rule_id: int,
    due_date: date,
) -> tuple[TaxCalendarEntry, bool]:
    """Idempotent. Returns (entry, created)."""
    query = db.query(TaxCalendarEntry).filter(
        TaxCalendarEntry.obligation_type == obligation_type.value,
    )
    if obligation_type is ObligationType.ANNUAL_REPORT:
        query = query.filter(TaxCalendarEntry.tax_year == tax_year)
    else:
        query = query.filter(TaxCalendarEntry.period == period).filter(
            TaxCalendarEntry.period_months_count == period_months_count
        )
    existing = query.one_or_none()
    if existing is not None:
        return existing, False

    entry = TaxCalendarEntry(
        obligation_type=obligation_type,
        period=period,
        period_months_count=period_months_count,
        tax_year=tax_year,
        due_date=due_date,
        deadline_rule_id=deadline_rule_id,
    )
    db.add(entry)
    db.flush()
    return entry, True


def _generate_periodic(
    db: Session,
    *,
    obligation_type,
    rule_type,
    tax_year,
    period_starts,
    period_months_count,
) -> int:
    rule = _resolve_rule(db, rule_type=rule_type, on_date=date(tax_year, 1, 1))
    created = 0
    for start_month in period_starts:
        period = f"{tax_year}-{start_month:02d}"
        due = periodic_due_date(rule, tax_year, start_month)
        _, was_created = get_or_create_entry(
            db,
            obligation_type=obligation_type,
            period=period,
            period_months_count=period_months_count,
            tax_year=tax_year,
            deadline_rule_id=rule.id,
            due_date=due,
        )
        if was_created:
            created += 1
    return created


def generate_for_year(db: Session, tax_year: int) -> dict[str, int]:
    """Generate every regulatory calendar entry for a tax year.

    Returns counts of newly-created rows per category. Idempotent.
    """
    counts: dict[str, int] = {}
    for obligation, rule_type, period_starts, months_count in _PERIODIC_PLAN:
        counts[_RULE_KEY[rule_type]] = _generate_periodic(
            db,
            obligation_type=obligation,
            rule_type=rule_type,
            tax_year=tax_year,
            period_starts=period_starts,
            period_months_count=months_count,
        )

    annual_rule = _resolve_rule(
        db,
        rule_type=DeadlineRuleType.ANNUAL_REPORT,
        on_date=date(tax_year + 1, 1, 1),
    )
    _, annual_created = get_or_create_entry(
        db,
        obligation_type=ObligationType.ANNUAL_REPORT,
        period=None,
        period_months_count=None,
        tax_year=tax_year,
        deadline_rule_id=annual_rule.id,
        due_date=annual_due_date(annual_rule, tax_year),
    )
    counts["annual_report"] = 1 if annual_created else 0
    return counts


def generate_for_year_range(
    db: Session,
    *,
    start_year: int,
    end_year: int,
) -> dict[int, dict[str, int]]:
    """Generate for [start_year, end_year] inclusive. Idempotent."""
    if end_year < start_year:
        raise ValueError(f"end_year ({end_year}) must be >= start_year ({start_year}).")
    return {y: generate_for_year(db, y) for y in range(start_year, end_year + 1)}
