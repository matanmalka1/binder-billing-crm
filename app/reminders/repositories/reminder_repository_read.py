"""Read-only list/count queries for ReminderRepository — split to stay under 150-line limit."""
from datetime import date

from sqlalchemy.orm import Session

from app.common.repositories.base_repository import BaseRepository
from app.reminders.models.reminder import Reminder, ReminderStatus


class ReminderRepositoryRead(BaseRepository):
    """List and count queries for Reminder entities."""

    def __init__(self, db: Session):
        super().__init__(db)

    def list_pending_by_date(
        self,
        reference_date: date,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Reminder]:
        query = (
            self.db.query(Reminder)
            .filter(
                Reminder.status == ReminderStatus.PENDING,
                Reminder.send_on <= reference_date,
                Reminder.deleted_at.is_(None),
            )
            .order_by(Reminder.send_on.asc())
        )
        return self._paginate(query, page, page_size)

    def count_pending_by_date(self, reference_date: date) -> int:
        return (
            self.db.query(Reminder)
            .filter(
                Reminder.status == ReminderStatus.PENDING,
                Reminder.send_on <= reference_date,
                Reminder.deleted_at.is_(None),
            )
            .count()
        )

    def list_by_status(
        self,
        status: ReminderStatus,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Reminder]:
        query = (
            self.db.query(Reminder)
            .filter(Reminder.status == status, Reminder.deleted_at.is_(None))
            .order_by(Reminder.created_at.desc())
        )
        return self._paginate(query, page, page_size)

    def count_by_status(self, status: ReminderStatus) -> int:
        return (
            self.db.query(Reminder)
            .filter(Reminder.status == status, Reminder.deleted_at.is_(None))
            .count()
        )

    def count_by_business(self, business_id: int) -> int:
        return (
            self.db.query(Reminder)
            .filter(Reminder.business_id == business_id, Reminder.deleted_at.is_(None))
            .count()
        )

    def list_by_business(
        self,
        business_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Reminder]:
        query = (
            self.db.query(Reminder)
            .filter(Reminder.business_id == business_id, Reminder.deleted_at.is_(None))
            .order_by(Reminder.created_at.desc())
        )
        return self._paginate(query, page, page_size)

    def list_by_client(
        self,
        client_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Reminder]:
        query = (
            self.db.query(Reminder)
            .filter(Reminder.client_id == client_id, Reminder.deleted_at.is_(None))
            .order_by(Reminder.created_at.desc())
        )
        return self._paginate(query, page, page_size)

    def list_by_client_record(
        self,
        client_record_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Reminder]:
        query = (
            self.db.query(Reminder)
            .filter(Reminder.client_record_id == client_record_id, Reminder.deleted_at.is_(None))
            .order_by(Reminder.created_at.desc())
        )
        return self._paginate(query, page, page_size)

    def count_by_client(self, client_id: int) -> int:
        return (
            self.db.query(Reminder)
            .filter(Reminder.client_id == client_id, Reminder.deleted_at.is_(None))
            .count()
        )

    def count_by_client_record(self, client_record_id: int) -> int:
        return (
            self.db.query(Reminder)
            .filter(Reminder.client_record_id == client_record_id, Reminder.deleted_at.is_(None))
            .count()
        )

    def exists_pending_for_tax_deadline(self, tax_deadline_id: int) -> bool:
        """Return True if a PENDING reminder for this tax deadline already exists."""
        return (
            self.db.query(Reminder.id)
            .filter(
                Reminder.tax_deadline_id == tax_deadline_id,
                Reminder.status == ReminderStatus.PENDING,
                Reminder.deleted_at.is_(None),
            )
            .first()
        ) is not None
