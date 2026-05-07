"""Local/dev bootstrap for tax calendar regulatory defaults."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.common.enums import DeadlineRuleType
from app.tax_calendar.models.deadline_rule import DeadlineRule
from app.tax_calendar.services.tax_calendar_entry_service import generate_for_year_range

DEFAULT_EFFECTIVE_FROM = date(2023, 1, 1)


@dataclass(frozen=True)
class DefaultDeadlineRule:
    rule_type: DeadlineRuleType
    due_day_of_month: int
    offset_months: int


DEFAULT_DEADLINE_RULES: tuple[DefaultDeadlineRule, ...] = (
    DefaultDeadlineRule(DeadlineRuleType.VAT_MONTHLY, 15, 1),
    DefaultDeadlineRule(DeadlineRuleType.VAT_BIMONTHLY, 15, 2),
    DefaultDeadlineRule(DeadlineRuleType.ADVANCE_MONTHLY, 15, 1),
    DefaultDeadlineRule(DeadlineRuleType.ADVANCE_BIMONTHLY, 15, 2),
    DefaultDeadlineRule(DeadlineRuleType.ANNUAL_REPORT, 31, 4),
)


def _has_open_ended_rule(db: Session, rule_type: DeadlineRuleType) -> bool:
    return (
        db.query(DeadlineRule.id)
        .filter(DeadlineRule.rule_type == rule_type.value)
        .filter(DeadlineRule.effective_to.is_(None))
        .first()
        is not None
    )


def seed_default_deadline_rules(db: Session) -> dict[str, int]:
    """Create missing open-ended default rules. Returns created counts by key."""
    created: dict[str, int] = {}
    for default in DEFAULT_DEADLINE_RULES:
        if _has_open_ended_rule(db, default.rule_type):
            created[default.rule_type.value] = 0
            continue
        db.add(
            DeadlineRule(
                rule_type=default.rule_type,
                due_day_of_month=default.due_day_of_month,
                offset_months=default.offset_months,
                effective_from=DEFAULT_EFFECTIVE_FROM,
                effective_to=None,
                description="Default local/dev tax calendar bootstrap rule",
            )
        )
        created[default.rule_type.value] = 1
    db.flush()
    return created


def default_year_range(today: date | None = None) -> tuple[int, int]:
    current_year = (today or date.today()).year
    return current_year, current_year + 1


def bootstrap_tax_calendar(
    db: Session,
    *,
    start_year: int | None = None,
    end_year: int | None = None,
    today: date | None = None,
) -> dict[str, object]:
    """Seed default rules and generate TaxCalendarEntry rows for a year range."""
    default_start, default_end = default_year_range(today)
    resolved_start = start_year if start_year is not None else default_start
    resolved_end = end_year if end_year is not None else default_end
    rules_created = seed_default_deadline_rules(db)
    entries_created = generate_for_year_range(
        db,
        start_year=resolved_start,
        end_year=resolved_end,
    )
    return {
        "start_year": resolved_start,
        "end_year": resolved_end,
        "rules_created": rules_created,
        "entries_created": entries_created,
    }
