from datetime import date, timedelta
from typing import Optional

from app.binders.models.binder import Binder, BinderStatus

# Number of days a binder may stay out before it's expected back.
BINDER_MAX_DAYS = 90


def calculate_expected_return(received_at: date) -> date:
    """Calculate expected return date (received + 90 days)."""
    return received_at + timedelta(days=BINDER_MAX_DAYS)


def validate_ready_transition(binder: Binder) -> None:
    """Validate binder can be marked ready for pickup."""
    if binder.status not in [BinderStatus.IN_OFFICE, BinderStatus.OVERDUE]:
        raise ValueError(f"Cannot mark binder as ready from status {binder.status}")


def validate_return_transition(
    binder: Binder, pickup_person_name: Optional[str]
) -> None:
    """Validate binder can be returned."""
    if not pickup_person_name or not pickup_person_name.strip():
        raise ValueError("pickup_person_name is required")

    if binder.status not in [BinderStatus.READY_FOR_PICKUP, BinderStatus.OVERDUE]:
        raise ValueError(f"Cannot return binder from status {binder.status}")
