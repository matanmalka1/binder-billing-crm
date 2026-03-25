import calendar
from datetime import date
from typing import Optional

from app.core.exceptions import AppError
from app.binders.models.binder import Binder, BinderStatus




def validate_ready_transition(binder: Binder) -> None:
    """Validate binder can be marked ready for pickup."""
    if binder.status != BinderStatus.IN_OFFICE:
        raise AppError(
            f"לא ניתן לסמן תיק כמוכן מסטטוס {binder.status}",
            "BINDER.INVALID_STATUS",
        )


def validate_return_transition(
    binder: Binder, pickup_person_name: Optional[str]
) -> None:
    """Validate binder can be returned."""
    if not pickup_person_name or not pickup_person_name.strip():
        raise AppError("שם האיש המאסף הוא שדה חובה", "BINDER.MISSING_PICKUP_PERSON")

    if binder.status != BinderStatus.READY_FOR_PICKUP:
        raise AppError(
            f"לא ניתן להחזיר תיק מסטטוס {binder.status}",
            "BINDER.INVALID_STATUS",
        )


def validate_revert_ready_transition(binder: Binder) -> None:
    """Validate binder can be reverted from READY_FOR_PICKUP back to IN_OFFICE."""
    if binder.status != BinderStatus.READY_FOR_PICKUP:
        raise AppError(
            f"לא ניתן לבטל סטטוס מוכן מסטטוס {binder.status}",
            "BINDER.INVALID_STATUS",
        )


def parse_period_to_date(period: str) -> Optional[date]:
    """
    Convert a period description string to a closing date.
      "2026-03"       → 2026-03-31  (monthly)
      "2026-01-02"    → 2026-02-28  (bimonthly — end of second month)
      "2026"          → 2026-12-31  (annual)
    Returns None if unparseable.
    """
    parts = period.strip().split("-")
    try:
        if len(parts) == 1:
            return date(int(parts[0]), 12, 31)
        if len(parts) == 2:
            year, month = int(parts[0]), int(parts[1])
            return date(year, month, calendar.monthrange(year, month)[1])
        if len(parts) == 3:
            year, month2 = int(parts[0]), int(parts[2])
            return date(year, month2, calendar.monthrange(year, month2)[1])
    except (ValueError, TypeError):
        return None
    return None
