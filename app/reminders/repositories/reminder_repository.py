from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.reminders.models.reminder import Reminder, ReminderStatus, ReminderType
from app.reminders.repositories.reminder_repository_read import ReminderRepositoryRead
from app.utils.time_utils import utcnow


class ReminderRepository(ReminderRepositoryRead):
    def __init__(self, db: Session):
        super().__init__(db)

    def create(
        self,
        reminder_type: ReminderType,
        target_date: date,
        days_before: int,
        send_on: date,
        message: str,
        client_record_id: int,
        business_id: Optional[int] = None,
        binder_id: Optional[int] = None,
        created_by: Optional[int] = None,
    ) -> Reminder:
        reminder = Reminder(
            client_record_id=client_record_id,
            business_id=business_id,
            reminder_type=reminder_type,
            target_date=target_date,
            days_before=days_before,
            send_on=send_on,
            message=message,
            status=ReminderStatus.PENDING,
            binder_id=binder_id,
            created_by=created_by,
        )
        self.db.add(reminder)
        self.db.flush()
        return reminder

    def update_status(
        self, reminder_id: int, new_status: ReminderStatus, **additional_fields
    ) -> Optional[Reminder]:
        reminder = self.get_by_id(reminder_id)
        if not reminder:
            return None
        reminder.status = new_status
        for field, value in additional_fields.items():
            setattr(reminder, field, value)
        self.db.flush()
        return reminder

    def cancel_pending_by_client_record(self, client_record_id: int) -> int:
        now = utcnow()
        rows = self.db.scalars(
            select(Reminder).where(
                Reminder.client_record_id == client_record_id,
                Reminder.status == ReminderStatus.PENDING,
                Reminder.deleted_at.is_(None),
            )
        ).all()
        for r in rows:
            r.status = ReminderStatus.CANCELED
            r.canceled_at = now
        if rows:
            self.db.flush()
        return len(rows)
