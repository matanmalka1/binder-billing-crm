from datetime import date, timedelta
from typing import Optional

from app.models import Binder, BinderStatus


class BinderHelpers:
    """Helper functions for binder business logic."""
    
    BINDER_MAX_DAYS = 90

    @staticmethod
    def calculate_expected_return(received_at: date) -> date:
        """Calculate expected return date (received + 90 days)."""
        return received_at + timedelta(days=BinderHelpers.BINDER_MAX_DAYS)

    @staticmethod
    def validate_ready_transition(binder: Binder) -> None:
        """Validate binder can be marked ready for pickup."""
        if binder.status not in [BinderStatus.IN_OFFICE, BinderStatus.OVERDUE]:
            raise ValueError(f"Cannot mark binder as ready from status {binder.status}")

    @staticmethod
    def validate_return_transition(binder: Binder, pickup_person_name: Optional[str]) -> None:
        """Validate binder can be returned."""
        if not pickup_person_name or not pickup_person_name.strip():
            raise ValueError("pickup_person_name is required")
        
        if binder.status not in [BinderStatus.READY_FOR_PICKUP, BinderStatus.OVERDUE]:
            raise ValueError(f"Cannot return binder from status {binder.status}")

    @staticmethod
    def is_overdue_eligible(binder: Binder, reference_date: date) -> bool:
        """Check if binder is eligible to be marked overdue."""
        return (
            binder.expected_return_at < reference_date
            and binder.status in [BinderStatus.IN_OFFICE, BinderStatus.READY_FOR_PICKUP]
        )