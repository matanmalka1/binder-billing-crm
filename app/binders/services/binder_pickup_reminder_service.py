"""Binder pickup reminder — sends a follow-up notification when client hasn't collected."""
from __future__ import annotations

import datetime as _dt
from datetime import timezone

from sqlalchemy.orm import Session

from app.binders.models.binder import BinderStatus
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.services.messages import BINDER_NOT_FOUND
from app.core.exceptions import AppError, NotFoundError
from app.notification.models.notification import NotificationTrigger
from app.notification.repositories.notification_repository import NotificationRepository
from app.notification.services.notification_service import NotificationService

_REMINDER_COOLDOWN_DAYS = 5


class BinderPickupReminderService:
    def __init__(self, db: Session):
        self.binder_repo = BinderRepository(db)
        self.notification_repo = NotificationRepository(db)
        self.notification_service = NotificationService(db)

    def send_pickup_reminder(self, binder_id: int, triggered_by: int) -> None:
        binder = self.binder_repo.get_by_id(binder_id)
        if not binder:
            raise NotFoundError(BINDER_NOT_FOUND.format(binder_id=binder_id), "BINDER.NOT_FOUND")

        if binder.status not in (BinderStatus.READY_FOR_PICKUP, BinderStatus.READY_FOR_PICKUP.value):
            raise AppError("הקלסר אינו במצב מוכן לאיסוף", "BINDER.NOT_READY_FOR_PICKUP")

        last = self.notification_repo.get_last_for_binder_trigger(
            binder_id, NotificationTrigger.PICKUP_REMINDER
        )
        if last:
            days_since = (_dt.datetime.now(timezone.utc) - last.created_at.replace(tzinfo=timezone.utc)).days
            if days_since < _REMINDER_COOLDOWN_DAYS:
                raise AppError(
                    f"תזכורת נשלחה לפני {days_since} ימים. ניתן לשלוח שוב לאחר {_REMINDER_COOLDOWN_DAYS} ימים.",
                    "BINDER.REMINDER_TOO_SOON",
                )

        self.notification_service.notify_pickup_reminder(
            binder=binder,
            client_record_id=binder.client_record_id,
            triggered_by=triggered_by,
        )
