from datetime import datetime
from typing import Any, Optional

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
        source_domain: Optional[str] = None,
        source_id: Optional[int] = None,
        target_task_id: Optional[int] = None,
        notification_template_key: Optional[str] = None,
        payload: Optional[dict[str, Any]] = None,
        created_by_user_id: Optional[int] = None,
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
    ) -> Optional[Reminder]:
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
        return self.db.scalar(
            select(func.count(Reminder.id)).where(Reminder.status == status)
        )

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
