from datetime import date, timedelta
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy.orm import Session

from app.binders.models.binder import Binder, BinderStatus
from app.notification.models.notification import Notification


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
        if reference_date is None:
            reference_date = date.today()

        if binder.status == BinderStatus.RETURNED:
            return WorkState.COMPLETED

        if binder.status == BinderStatus.READY_FOR_PICKUP:
            return WorkState.IN_PROGRESS

        days_since_start = (reference_date - binder.period_start).days
        if days_since_start < WorkStateService.IDLE_THRESHOLD_DAYS:
            return WorkState.IN_PROGRESS

        if db is not None:
            if WorkStateService._has_recent_notification_activity(binder, reference_date, db):
                return WorkState.IN_PROGRESS

        return WorkState.WAITING_FOR_WORK

    @staticmethod
    def _has_recent_notification_activity(
        binder: Binder,
        reference_date: date,
        db: Session,
    ) -> bool:
        """
        Check for notifications linked directly to this binder within the idle threshold.

        Queries by binder_id (not business_id/client_id) to avoid false positives
        from notifications on other binders of the same client.
        """
        threshold_date = reference_date - timedelta(days=WorkStateService.IDLE_THRESHOLD_DAYS)

        count = (
            db.query(Notification)
            .filter(
                Notification.binder_id == binder.id,
                Notification.created_at >= threshold_date,
            )
            .limit(1)
            .count()
        )
        return count > 0

    @staticmethod
    def is_idle(
        binder: Binder,
        reference_date: Optional[date] = None,
        db: Optional[Session] = None,
    ) -> bool:
        state = WorkStateService.derive_work_state(binder, reference_date, db)
        return state == WorkState.WAITING_FOR_WORK