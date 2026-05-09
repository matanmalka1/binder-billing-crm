"""Read-only list/count queries for ReminderRepository."""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.clients.repositories.active_client_scope import scope_to_active_clients_stmt
from app.common.repositories.base_repository import BaseRepository
from app.reminders.models.reminder import Reminder, ReminderStatus


class ReminderRepositoryRead(BaseRepository):
    model = Reminder

    def __init__(self, db: Session):
        super().__init__(db)

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
        """Count PENDING manual reminders whose send_on date is on or before reference_date."""
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
