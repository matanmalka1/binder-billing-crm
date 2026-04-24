from datetime import date

from app.tax_deadline.models.tax_deadline import TaxDeadline, TaxDeadlineStatus, UrgencyLevel
from app.tax_deadline.services.constants import URGENCY_CRITICAL_DAYS, URGENCY_WARNING_DAYS


def compute_deadline_urgency(
    deadline: TaxDeadline,
    reference_date: date | None = None,
) -> UrgencyLevel:
    if deadline.status in (TaxDeadlineStatus.COMPLETED, TaxDeadlineStatus.CANCELED):
        return UrgencyLevel.NONE
    if reference_date is None:
        reference_date = date.today()

    days_remaining = (deadline.due_date - reference_date).days
    if days_remaining < 0:
        return UrgencyLevel.OVERDUE
    if days_remaining <= URGENCY_CRITICAL_DAYS:
        return UrgencyLevel.CRITICAL
    if days_remaining <= URGENCY_WARNING_DAYS:
        return UrgencyLevel.WARNING
    return UrgencyLevel.NORMAL

