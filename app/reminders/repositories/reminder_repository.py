from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.common.repositories import BaseRepository
from app.reminders.models.reminder import Reminder, ReminderStatus, ReminderType


class ReminderRepository(BaseRepository):
    """Data access layer for Reminder entities."""

    def __init__(self, db: Session):
        super().__init__(db)

    def create(
        self,
        client_id: int,
        reminder_type: ReminderType,
        target_date: date,
        days_before: int,
        send_on: date,
        message: str,
        binder_id: Optional[int] = None,
        charge_id: Optional[int] = None,
        tax_deadline_id: Optional[int] = None,
    ) -> Reminder:
        """Create new reminder."""
        reminder = Reminder(
            client_id=client_id,
            reminder_type=reminder_type,
            target_date=target_date,
            days_before=days_before,
            send_on=send_on,
            message=message,
            status=ReminderStatus.PENDING,
            binder_id=binder_id,
            charge_id=charge_id,
            tax_deadline_id=tax_deadline_id,
        )
        self.db.add(reminder)
        self.db.commit()
        self.db.refresh(reminder)
        return reminder

    def get_by_id(self, reminder_id: int) -> Optional[Reminder]:
        """Retrieve reminder by ID."""
        return self.db.query(Reminder).filter(Reminder.id == reminder_id).first()

    def list_pending_by_date(
        self,
        reference_date: date,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Reminder]:
        """List pending reminders that should be sent on or before reference_date."""
        query = (
            self.db.query(Reminder)
            .filter(
                Reminder.status == ReminderStatus.PENDING,
                Reminder.send_on <= reference_date,
            )
            .order_by(Reminder.send_on.asc())
        )

        return self._paginate(query, page, page_size)

    def count_pending_by_date(self, reference_date: date) -> int:
        """Count pending reminders."""
        return (
            self.db.query(Reminder)
            .filter(
                Reminder.status == ReminderStatus.PENDING,
                Reminder.send_on <= reference_date,
            )
            .count()
        )

    def list_by_status(
        self,
        status: ReminderStatus,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Reminder]:
        """List reminders by status."""
        query = (
            self.db.query(Reminder)
            .filter(Reminder.status == status)
            .order_by(Reminder.created_at.desc())
        )

        return self._paginate(query, page, page_size)

    def count_by_status(self, status: ReminderStatus) -> int:
        """Count reminders by status."""
        return self.db.query(Reminder).filter(Reminder.status == status).count()

    def update_status(
        self,
        reminder_id: int,
        new_status: ReminderStatus,
        **additional_fields,
    ) -> Optional[Reminder]:
        """Update reminder status and additional fields."""
        reminder = self.get_by_id(reminder_id)
        return self._update_status(reminder, new_status, **additional_fields)
