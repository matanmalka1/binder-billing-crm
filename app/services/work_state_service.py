from datetime import date, timedelta
from enum import Enum as PyEnum
from typing import Optional

from app.models import Binder, BinderStatus


class WorkState(str, PyEnum):
    """Derived operational work state (NOT persisted)."""
    
    WAITING_FOR_WORK = "waiting_for_work"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class WorkStateService:
    """Derive operational work state for binders."""

    IDLE_THRESHOLD_DAYS = 14

    @staticmethod
    def derive_work_state(
        binder: Binder,
        reference_date: Optional[date] = None,
    ) -> WorkState:
        """
        Derive work state from binder properties.
        
        Logic:
        - COMPLETED: status == RETURNED
        - IN_PROGRESS: received within last 14 days OR ready_for_pickup
        - WAITING_FOR_WORK: older than 14 days, not returned, not ready
        
        Args:
            binder: Binder entity
            reference_date: Date for calculation (defaults to today)
        
        Returns:
            Derived WorkState (not persisted)
        """
        if reference_date is None:
            reference_date = date.today()

        # Completed work
        if binder.status == BinderStatus.RETURNED:
            return WorkState.COMPLETED

        # In progress: ready for pickup
        if binder.status == BinderStatus.READY_FOR_PICKUP:
            return WorkState.IN_PROGRESS

        # In progress: recently received (within threshold)
        days_since_received = (reference_date - binder.received_at).days
        if days_since_received < WorkStateService.IDLE_THRESHOLD_DAYS:
            return WorkState.IN_PROGRESS

        # Waiting for work: older, not completed, not ready
        return WorkState.WAITING_FOR_WORK

    @staticmethod
    def is_idle(
        binder: Binder,
        reference_date: Optional[date] = None,
    ) -> bool:
        """Check if binder is idle (waiting for work)."""
        state = WorkStateService.derive_work_state(binder, reference_date)
        return state == WorkState.WAITING_FOR_WORK