from datetime import date, timedelta
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy.orm import Session

from app.binders.models.binder import Binder, BinderStatus
from app.notification.repositories.notification_repository import NotificationRepository



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
        db: Optional[Session] = None,
    ) -> WorkState:
        """
        Derive work state from binder properties.
        
        Sprint 6: Now incorporates notification history as input.
        
        Logic:
        - COMPLETED: status == RETURNED
        - IN_PROGRESS: received within last 14 days OR ready_for_pickup OR recent notification activity
        - WAITING_FOR_WORK: older than 14 days, not returned, not ready, no recent activity
        
        Args:
            binder: Binder entity
            reference_date: Date for calculation (defaults to today)
            db: Database session (optional, for notification history)
        
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

        # Sprint 6: Check notification history for recent activity
        if db is not None:
            if WorkStateService._has_recent_notification_activity(
                binder, reference_date, db
            ):
                return WorkState.IN_PROGRESS

        # Waiting for work: older, not completed, not ready, no recent activity
        return WorkState.WAITING_FOR_WORK

    @staticmethod
    def _has_recent_notification_activity(
        binder: Binder,
        reference_date: date,
        db: Session,
    ) -> bool:
        """
        Check if binder has notification activity within the idle threshold.
        
        Sprint 6 addition: Recent notifications indicate active work.
        """
        
        notification_repo = NotificationRepository(db)
        
        # Get all notifications for this binder
        # Note: list_by_binder doesn't exist in NotificationRepository
        # We need to check by client_id instead
        notifications = notification_repo.list_by_client(
            binder.client_id, page=1, page_size=100
        )
        
        # Filter to this specific binder
        binder_notifications = [
            n for n in notifications if n.binder_id == binder.id
        ]
        
        if not binder_notifications:
            return False
        
        # Check if any notification was created within the threshold
        threshold_date = reference_date - timedelta(days=WorkStateService.IDLE_THRESHOLD_DAYS)
        
        for notification in binder_notifications:
            if notification.created_at.date() >= threshold_date:
                return True
        
        return False

    @staticmethod
    def is_idle(
        binder: Binder,
        reference_date: Optional[date] = None,
        db: Optional[Session] = None,
    ) -> bool:
        """Check if binder is idle (waiting for work)."""
        state = WorkStateService.derive_work_state(binder, reference_date, db)
        return state == WorkState.WAITING_FOR_WORK
