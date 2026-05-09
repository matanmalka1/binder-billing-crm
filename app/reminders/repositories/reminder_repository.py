from datetime import date, datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.clients.repositories.active_client_scope import scope_to_active_clients_stmt
from app.common.repositories.base_repository import BaseRepository
from app.reminders.models.reminder import Reminder, ReminderStatus, ReminderType
from app.utils.time_utils import utcnow


class ReminderRepository(BaseRepository):
    model = Reminder

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

    def _active_client_stmt(self):
        return scope_to_active_clients_stmt(select(Reminder), Reminder)

    def list_by_status(
        self,
        status: ReminderStatus,
        page: int = 1,
        page_size: int = 20,
        created_before: Optional[datetime] = None,
    ) -> list[Reminder]:
        stmt = self._active_client_stmt().where(
            Reminder.status == status,
            Reminder.deleted_at.is_(None),
        )
        if created_before is not None:
            stmt = stmt.where(Reminder.created_at <= created_before)
        stmt = stmt.order_by(Reminder.created_at.desc())
        stmt = self.apply_pagination(stmt, page, page_size)
        return list(self.db.scalars(stmt).all())

    def count_by_status(
        self, status: ReminderStatus, created_before: Optional[datetime] = None
    ) -> int:
        stmt = scope_to_active_clients_stmt(
            select(func.count(Reminder.id)), Reminder
        ).where(
            Reminder.status == status,
            Reminder.deleted_at.is_(None),
        )
        if created_before is not None:
            stmt = stmt.where(Reminder.created_at <= created_before)
        return self.db.scalar(stmt)

    def count_due_now(self, reference_date: date) -> int:
        stmt = scope_to_active_clients_stmt(
            select(func.count(Reminder.id)), Reminder
        ).where(
            Reminder.status == ReminderStatus.PENDING,
            Reminder.send_on <= reference_date,
            Reminder.deleted_at.is_(None),
        )
        return self.db.scalar(stmt)

    def count_by_business(self, business_id: int) -> int:
        return self.db.scalar(
            select(func.count(Reminder.id)).where(
                Reminder.business_id == business_id, Reminder.deleted_at.is_(None)
            )
        )

    def list_by_business(
        self, business_id: int, page: int = 1, page_size: int = 20
    ) -> list[Reminder]:
        stmt = (
            select(Reminder)
            .where(
                Reminder.business_id == business_id,
                Reminder.deleted_at.is_(None),
            )
            .order_by(Reminder.created_at.desc())
        )
        stmt = self.apply_pagination(stmt, page, page_size)
        return list(self.db.scalars(stmt).all())

    def list_by_client_record(
        self, client_record_id: int, page: int = 1, page_size: int = 20
    ) -> list[Reminder]:
        stmt = (
            select(Reminder)
            .where(
                Reminder.client_record_id == client_record_id,
                Reminder.deleted_at.is_(None),
            )
            .order_by(Reminder.created_at.desc())
        )
        stmt = self.apply_pagination(stmt, page, page_size)
        return list(self.db.scalars(stmt).all())

    def count_by_client_record(self, client_record_id: int) -> int:
        return self.db.scalar(
            select(func.count(Reminder.id)).where(
                Reminder.client_record_id == client_record_id,
                Reminder.deleted_at.is_(None),
            )
        )
