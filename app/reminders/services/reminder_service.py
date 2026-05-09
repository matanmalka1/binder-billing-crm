from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, NotFoundError
from app.reminders.models.reminder import Reminder, ReminderStatus
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.reminders.schemas.reminders import ReminderCreateRequest


class ReminderService:
    def __init__(self, db: Session):
        self.db = db
        self.reminder_repo = ReminderRepository(db)

    def create_from_request(
        self, request: ReminderCreateRequest, *, created_by_user_id: int
    ) -> Reminder:
        return self.reminder_repo.create(
            fire_at=request.fire_at,
            action_type=request.action_type,
            source_domain=request.source_domain,
            source_id=request.source_id,
            target_task_id=request.target_task_id,
            notification_template_key=request.notification_template_key,
            payload=request.payload,
            created_by_user_id=created_by_user_id,
        )

    def get_reminders(
        self, *, status: Optional[str] = None, page: int = 1, page_size: int = 20
    ) -> tuple[list[Reminder], int]:
        status_enum = self._parse_status(status)
        items = self.reminder_repo.list_by_status(status_enum, page, page_size)
        total = self.reminder_repo.count_by_status(status_enum)
        return items, total

    def get_reminder(self, reminder_id: int) -> Optional[Reminder]:
        return self.reminder_repo.get_by_id(reminder_id)

    def cancel_reminder(self, reminder_id: int) -> Reminder:
        reminder = self.reminder_repo.get_by_id(reminder_id)
        if reminder is None:
            raise NotFoundError("התזכורת לא נמצאה", "REMINDER.NOT_FOUND")
        if reminder.status != ReminderStatus.SCHEDULED:
            raise AppError(
                "ניתן לבטל רק טריגר מתוזמן",
                "REMINDER.INVALID_STATUS",
            )
        return self.reminder_repo.update_status(reminder_id, ReminderStatus.CANCELED)

    def _parse_status(self, status: Optional[str]) -> ReminderStatus:
        if status is None:
            return ReminderStatus.SCHEDULED
        valid_statuses = {item.value for item in ReminderStatus}
        if status not in valid_statuses:
            raise AppError(
                f"סטטוס לא חוקי: {status}. חייב להיות אחד מהבאים: {', '.join(valid_statuses)}",
                "REMINDER.INVALID_STATUS",
            )
        return ReminderStatus(status)
