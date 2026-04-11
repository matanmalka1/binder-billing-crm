from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.reminders.models.reminder import Reminder, ReminderStatus, ReminderType
from app.reminders.repositories.reminder_repository_flush import ReminderRepositoryFlush
from app.utils.time_utils import utcnow


class ReminderRepository(ReminderRepositoryFlush):
    """Data access layer for Reminder entities."""

    def __init__(self, db: Session):
        super().__init__(db)

    def create(
        self,
        reminder_type: ReminderType,
        target_date: date,
        days_before: int,
        send_on: date,
        message: str,
        business_id: Optional[int] = None,
        client_id: Optional[int] = None,
        binder_id: Optional[int] = None,
        charge_id: Optional[int] = None,
        tax_deadline_id: Optional[int] = None,
        annual_report_id: Optional[int] = None,
        advance_payment_id: Optional[int] = None,
        created_by: Optional[int] = None,
    ) -> Reminder:
        if (business_id is None) == (client_id is None):
            raise AppError(
                "תזכורת חייבת לשייך לעסק או ללקוח — לא לשניהם ולא לאף אחד",
                "REMINDER.INVALID_OWNER",
            )
        reminder = Reminder(
            business_id=business_id,
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
            annual_report_id=annual_report_id,
            advance_payment_id=advance_payment_id,
            created_by=created_by,
        )
        self.db.add(reminder)
        self.db.commit()
        self.db.refresh(reminder)
        return reminder

    def get_by_id(self, reminder_id: int) -> Optional[Reminder]:
        return (
            self.db.query(Reminder)
            .filter(Reminder.id == reminder_id, Reminder.deleted_at.is_(None))
            .first()
        )

    def claim_for_processing(self, reminder_id: int) -> Optional[Reminder]:
        """Transition PENDING → PROCESSING. Returns None if already claimed/sent."""
        reminder = self.get_by_id(reminder_id)
        if not reminder or reminder.status != ReminderStatus.PENDING:
            return None
        reminder.status = ReminderStatus.PROCESSING
        self.db.commit()
        self.db.refresh(reminder)
        return reminder

    def update_status(
        self,
        reminder_id: int,
        new_status: ReminderStatus,
        **additional_fields,
    ) -> Optional[Reminder]:
        reminder = self.get_by_id(reminder_id)
        return self._update_status(reminder, new_status, **additional_fields)

    def exists_vat_compliance_reminder(self, client_id: int, period: str) -> bool:
        """True if a VAT_FILING reminder for this client+period is already PENDING or SENT."""
        return (
            self.db.query(Reminder)
            .filter(
                Reminder.client_id == client_id,
                Reminder.reminder_type == ReminderType.VAT_FILING,
                Reminder.message.contains(period),
                Reminder.status.in_([ReminderStatus.PENDING, ReminderStatus.SENT]),
                Reminder.deleted_at.is_(None),
            )
            .first()
        ) is not None

    def _cancel_pending_by(self, field, value: int) -> int:
        now = utcnow()
        rows = (
            self.db.query(Reminder)
            .filter(field == value, Reminder.status == ReminderStatus.PENDING, Reminder.deleted_at.is_(None))
            .all()
        )
        for r in rows:
            r.status = ReminderStatus.CANCELED
            r.canceled_at = now
        if rows:
            self.db.commit()
        return len(rows)

    def cancel_pending_by_tax_deadline(self, tax_deadline_id: int) -> int:
        """Cancel all PENDING reminders linked to a tax deadline. Returns count canceled."""
        return self._cancel_pending_by(Reminder.tax_deadline_id, tax_deadline_id)

    def cancel_pending_by_charge(self, charge_id: int) -> int:
        """Cancel all PENDING reminders linked to a charge. Returns count canceled."""
        return self._cancel_pending_by(Reminder.charge_id, charge_id)
