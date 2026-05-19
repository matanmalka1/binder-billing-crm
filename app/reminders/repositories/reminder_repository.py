from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.common.repositories.base_repository import BaseRepository
from app.reminders.models.reminder import (
    Reminder,
    ReminderActionType,
    ReminderStatus,
)


class ReminderRepository(BaseRepository):
    model = Reminder

    def __init__(self, db: Session):
        super().__init__(db)

    def create(
        self,
        *,
        fire_at: datetime,
        action_type: ReminderActionType,
        source_domain: str | None = None,
        source_id: int | None = None,
        target_task_id: int | None = None,
        notification_template_key: str | None = None,
        payload: dict[str, Any] | None = None,
        created_by_user_id: int | None = None,
    ) -> Reminder:
        reminder = Reminder(
            fire_at=fire_at,
            action_type=action_type,
            status=ReminderStatus.SCHEDULED,
            source_domain=source_domain,
            source_id=source_id,
            target_task_id=target_task_id,
            notification_template_key=notification_template_key,
            payload=payload,
            created_by_user_id=created_by_user_id,
        )
        self.db.add(reminder)
        self.db.flush()
        return reminder

    def update_status(
        self, reminder_id: int, new_status: ReminderStatus, **fields
    ) -> Reminder | None:
        reminder = self.get_by_id(reminder_id)
        if not reminder:
            return None
        reminder.status = new_status
        for field, value in fields.items():
            setattr(reminder, field, value)
        self.db.flush()
        return reminder

    def list_by_status(
        self,
        status: ReminderStatus,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Reminder]:
        stmt = (
            select(Reminder)
            .where(Reminder.status == status)
            .order_by(Reminder.fire_at.asc(), Reminder.id.asc())
        )
        return list(self.db.scalars(self.apply_pagination(stmt, page, page_size)))

    def count_by_status(self, status: ReminderStatus) -> int:
        return self.db.scalar(select(func.count(Reminder.id)).where(Reminder.status == status))

    def list_due_scheduled(self, now: datetime, limit: int = 100) -> list[Reminder]:
        stmt = (
            select(Reminder)
            .where(
                Reminder.status == ReminderStatus.SCHEDULED,
                Reminder.fire_at <= now,
            )
            .order_by(Reminder.fire_at.asc(), Reminder.id.asc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())
