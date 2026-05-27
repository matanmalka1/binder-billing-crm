"""Binder handover reminder."""

from __future__ import annotations

import datetime as _dt

from sqlalchemy.orm import Session

from app.binders.models.binder import BinderLocationStatus
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.services.messages import BINDER_NOT_FOUND
from app.core.exceptions import AppError, NotFoundError
from app.notification.models.notification import NotificationTrigger
from app.notification.repositories.notification_repository import NotificationRepository
from app.notification.services.constants import HANDOVER_REMINDER_COOLDOWN_DAYS
from app.notification.services.notification_service import NotificationService


class BinderHandoverReminderService:
    def __init__(self, db: Session):
        self.binder_repo = BinderRepository(db)
        self.notification_repo = NotificationRepository(db)
        self.notification_service = NotificationService(db)

    def send_handover_reminder(self, binder_id: int, triggered_by: int) -> None:
        binder = self.binder_repo.get_by_id(binder_id)
        if not binder:
            raise NotFoundError(BINDER_NOT_FOUND.format(binder_id=binder_id), "BINDER.NOT_FOUND")

        if binder.location_status not in (
            BinderLocationStatus.READY_FOR_HANDOVER,
            BinderLocationStatus.READY_FOR_HANDOVER.value,
        ):
            raise AppError("הקלסר אינו מוכן למסירה", "BINDER.NOT_READY_FOR_HANDOVER")

        last = self.notification_repo.get_last_for_binder_trigger(
            binder_id, NotificationTrigger.BINDER_GENERAL_REMINDER
        )
        if last:
            days_since = (_dt.datetime.now(_dt.UTC) - last.created_at.replace(tzinfo=_dt.UTC)).days
            if days_since < HANDOVER_REMINDER_COOLDOWN_DAYS:
                raise AppError(
                    f"תזכורת נשלחה לפני {days_since} ימים. ניתן לשלוח שוב לאחר {HANDOVER_REMINDER_COOLDOWN_DAYS} ימים.",
                    "BINDER.REMINDER_TOO_SOON",
                )

        self.notification_service.notify_client(
            client_record_id=binder.client_record_id,
            trigger=NotificationTrigger.BINDER_GENERAL_REMINDER,
            template_data={"binder_number": binder.binder_number},
            binder_id=binder.id,
            triggered_by=triggered_by,
        )
