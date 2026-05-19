"""DeadlineRule service helpers.

INV-11: DeadlineRule overlap is enforced in the service layer, not by
DB constraint. Two rules of the same rule_type whose effective ranges
overlap are forbidden.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.common.enums import DeadlineRuleType
from app.tax_calendar.models.deadline_rule import DeadlineRule


def has_overlapping_rule(
    db: Session,
    *,
    rule_type: DeadlineRuleType,
    effective_from: date,
    effective_to: date | None,
    exclude_id: int | None = None,
) -> bool:
    """Return True if any existing DeadlineRule of the same rule_type
    has an effective range that intersects [effective_from, effective_to].

    Treats null effective_to as +infinity. Pure read; never raises on
    mere overlap. Caller decides how to react.
    """
    candidate_value = rule_type.value if isinstance(rule_type, DeadlineRuleType) else rule_type
    query = db.query(DeadlineRule).filter(DeadlineRule.rule_type == candidate_value)
    if exclude_id is not None:
        query = query.filter(DeadlineRule.id != exclude_id)

    for existing in query.all():
        existing_to = existing.effective_to
        # Two ranges [a1, a2] and [b1, b2] overlap iff a1 <= b2 and b1 <= a2,
        # treating null upper bound as +infinity.
        if effective_to is not None and existing.effective_from > effective_to:
            continue
        if existing_to is not None and effective_from > existing_to:
            continue
        return True
    return False
