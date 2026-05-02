"""Read-only list/count queries for ReminderRepository."""
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.clients.repositories.active_client_scope import scope_to_active_clients
from app.common.repositories.base_repository import BaseRepository
from app.reminders.models.reminder import Reminder, ReminderStatus


class ReminderRepositoryRead(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db)

    def _active_client_query(self):
        return scope_to_active_clients(self.db.query(Reminder), Reminder)

    def list_by_status(self, status: ReminderStatus, page: int = 1, page_size: int = 20, created_before: Optional[datetime] = None) -> list[Reminder]:
        query = self._active_client_query().filter(Reminder.status == status, Reminder.deleted_at.is_(None))
        if created_before is not None:
            query = query.filter(Reminder.created_at <= created_before)
        return self._paginate(query.order_by(Reminder.created_at.desc()), page, page_size)

    def count_by_status(self, status: ReminderStatus, created_before: Optional[datetime] = None) -> int:
        query = self._active_client_query().filter(Reminder.status == status, Reminder.deleted_at.is_(None))
        if created_before is not None:
            query = query.filter(Reminder.created_at <= created_before)
        return query.count()

    def count_by_business(self, business_id: int) -> int:
        return self.db.query(Reminder).filter(Reminder.business_id == business_id, Reminder.deleted_at.is_(None)).count()

    def list_by_business(self, business_id: int, page: int = 1, page_size: int = 20) -> list[Reminder]:
        query = self.db.query(Reminder).filter(Reminder.business_id == business_id, Reminder.deleted_at.is_(None)).order_by(Reminder.created_at.desc())
        return self._paginate(query, page, page_size)

    def list_by_client_record(self, client_record_id: int, page: int = 1, page_size: int = 20) -> list[Reminder]:
        query = self.db.query(Reminder).filter(Reminder.client_record_id == client_record_id, Reminder.deleted_at.is_(None)).order_by(Reminder.created_at.desc())
        return self._paginate(query, page, page_size)

    def count_by_client_record(self, client_record_id: int) -> int:
        return self.db.query(Reminder).filter(Reminder.client_record_id == client_record_id, Reminder.deleted_at.is_(None)).count()
