"""Builders for the grouped tax deadline read model."""

from datetime import date
from decimal import Decimal

from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadline, TaxDeadlineStatus, UrgencyLevel
from app.tax_deadline.schemas.grouped_deadline import DeadlineGroup, DeadlineGroupKey, DeadlineGroupPeriod
from app.tax_deadline.services.urgency import compute_deadline_urgency

_URGENCY_ORDER = {
    UrgencyLevel.OVERDUE: 0,
    UrgencyLevel.CRITICAL: 1,
    UrgencyLevel.WARNING: 2,
    UrgencyLevel.NORMAL: 3,
    UrgencyLevel.NONE: 4,
}


def build_group_key(deadline_type, due_date: date) -> str:
    type_str = deadline_type.value if hasattr(deadline_type, "value") else str(deadline_type)
    return f"{type_str}__{due_date.isoformat()}"


def parse_group_key(group_key: str) -> DeadlineGroupKey | None:
    parts = group_key.split("__")
    if len(parts) != 2:
        return None
    deadline_type_raw, due_date_str = parts
    try:
        due_date = date.fromisoformat(due_date_str)
    except ValueError:
        return None
    return DeadlineGroupKey(deadline_type=deadline_type_raw, due_date=due_date)


def build_group(group_key: str, items: list[TaxDeadline]) -> DeadlineGroup:
    today = date.today()
    urgencies = [compute_deadline_urgency(d, today) for d in items]
    pending = [d for d in items if d.status == TaxDeadlineStatus.PENDING]
    completed = [d for d in items if d.status == TaxDeadlineStatus.COMPLETED]
    amounts = [Decimal(str(d.payment_amount)) for d in items if d.payment_amount is not None]
    open_amounts = [Decimal(str(d.payment_amount)) for d in pending if d.payment_amount is not None]

    representative = items[0]
    return DeadlineGroup(
        group_key=group_key,
        deadline_type=representative.deadline_type,
        period=representative.period,
        period_months_count=_group_period_months_count(representative),
        tax_year=representative.tax_year,
        periods=_group_periods(items),
        tax_years=sorted({d.tax_year for d in items if d.tax_year is not None}),
        due_date=representative.due_date,
        total_clients=len(items),
        pending_count=len(pending),
        completed_count=len(completed),
        canceled_count=len(items) - len(pending) - len(completed),
        overdue_count=sum(1 for u in urgencies if u == UrgencyLevel.OVERDUE),
        total_amount=sum(amounts) if amounts else None,
        open_amount=sum(open_amounts) if open_amounts else None,
        worst_urgency=_worst_urgency(urgencies),
    )


def _worst_urgency(urgencies: list[UrgencyLevel]) -> UrgencyLevel:
    if not urgencies:
        return UrgencyLevel.NONE
    return min(urgencies, key=lambda u: _URGENCY_ORDER[u])


def _group_period_months_count(deadline: TaxDeadline) -> int | None:
    if deadline.deadline_type != DeadlineType.ADVANCE_PAYMENT or not deadline.period:
        return None
    start_month = int(deadline.period[-2:])
    due_month = deadline.due_date.month
    expected_bimonthly_due_month = start_month + 2
    if expected_bimonthly_due_month > 12:
        expected_bimonthly_due_month -= 12
    return 2 if due_month == expected_bimonthly_due_month else 1


def _group_periods(items: list[TaxDeadline]) -> list[DeadlineGroupPeriod]:
    seen = set()
    periods = []
    for item in items:
        if item.period is None:
            continue
        months_count = _group_period_months_count(item)
        key = (item.period, months_count)
        if key in seen:
            continue
        seen.add(key)
        periods.append(DeadlineGroupPeriod(period=item.period, period_months_count=months_count))
    return periods
