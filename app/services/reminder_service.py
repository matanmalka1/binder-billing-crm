from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Reminder, ReminderStatus, ReminderType
from app.repositories.client_repository import ClientRepository
from app.repositories.reminder_repository import ReminderRepository
from app.utils.time import utcnow


class ReminderService:
    """
    Proactive reminder management business logic.

    Handles:
    - Tax deadline reminders (X days before due date)
    - Idle binder reminders (X days without activity)
    - Unpaid charge reminders (X days after issue date)
    - Custom reminders (free-form, no foreign key required)

    Follows strict layering: Service → Repository → ORM
    """

    def __init__(self, db: Session):
        self.db = db
        self.reminder_repo = ReminderRepository(db)
        self.client_repo = ClientRepository(db)

    def create_tax_deadline_reminder(
        self,
        client_id: int,
        tax_deadline_id: int,
        target_date: date,
        days_before: int,
        message: Optional[str] = None,
    ) -> Reminder:
        """
        Create reminder for tax deadline.

        Business rules:
        - Client must exist
        - send_on = target_date - days_before
        - Default message if not provided

        Raises:
            ValueError: If client not found or invalid parameters
        """
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise ValueError(f"Client {client_id} not found")

        if days_before < 0:
            raise ValueError("days_before must be non-negative")

        send_on = target_date - timedelta(days=days_before)

        if message is None:
            message = f"תזכורת: מועד מס בעוד {days_before} ימים ({target_date})"

        return self.reminder_repo.create(
            client_id=client_id,
            reminder_type=ReminderType.TAX_DEADLINE_APPROACHING,
            target_date=target_date,
            days_before=days_before,
            send_on=send_on,
            message=message,
            tax_deadline_id=tax_deadline_id,
        )

    def create_idle_binder_reminder(
        self,
        client_id: int,
        binder_id: int,
        days_idle: int,
        message: Optional[str] = None,
    ) -> Reminder:
        """
        Create reminder for idle binder.

        Business rules:
        - Client must exist
        - days_idle determines urgency
        - send_on = today (immediate)

        Raises:
            ValueError: If client not found or invalid parameters
        """
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise ValueError(f"Client {client_id} not found")

        if days_idle < 0:
            raise ValueError("days_idle must be non-negative")

        target_date = date.today() + timedelta(days=days_idle)
        send_on = date.today()

        if message is None:
            message = f"תזכורת: תיק לא טופל {days_idle} ימים"

        return self.reminder_repo.create(
            client_id=client_id,
            reminder_type=ReminderType.BINDER_IDLE,
            target_date=target_date,
            days_before=0,
            send_on=send_on,
            message=message,
            binder_id=binder_id,
        )

    def create_unpaid_charge_reminder(
        self,
        client_id: int,
        charge_id: int,
        days_unpaid: int,
        message: Optional[str] = None,
    ) -> Reminder:
        """
        Create reminder for unpaid charge.

        Business rules:
        - Client must exist
        - days_unpaid indicates how long charge has been unpaid
        - send_on = today (immediate)

        Raises:
            ValueError: If client not found or invalid parameters
        """
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise ValueError(f"Client {client_id} not found")

        if days_unpaid < 0:
            raise ValueError("days_unpaid must be non-negative")

        target_date = date.today()
        send_on = date.today()

        if message is None:
            message = f"תזכורת: חשבונית לא שולמה {days_unpaid} ימים"

        return self.reminder_repo.create(
            client_id=client_id,
            reminder_type=ReminderType.UNPAID_CHARGE,
            target_date=target_date,
            days_before=0,
            send_on=send_on,
            message=message,
            charge_id=charge_id,
        )

    def create_custom_reminder(
        self,
        client_id: int,
        target_date: date,
        days_before: int,
        message: str,
    ) -> Reminder:
        """
        Create a free-form custom reminder.

        Business rules:
        - Client must exist
        - message is required (no meaningful default for free-form)
        - send_on = target_date - days_before
        - No foreign key required

        Raises:
            ValueError: If client not found or invalid parameters
        """
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise ValueError(f"Client {client_id} not found")

        if days_before < 0:
            raise ValueError("days_before must be non-negative")

        if not message or not message.strip():
            raise ValueError("message is required for custom reminders")

        send_on = target_date - timedelta(days=days_before)

        return self.reminder_repo.create(
            client_id=client_id,
            reminder_type=ReminderType.CUSTOM,
            target_date=target_date,
            days_before=days_before,
            send_on=send_on,
            message=message.strip(),
        )

    def get_reminders(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Reminder], int]:
        """
        List reminders with optional status filter.

        When no status is provided, returns pending reminders due today or earlier
        (operational default — the work queue view).

        When status is provided, returns all reminders of that status regardless
        of send_on date (history/audit view).

        Returns (items, total) for pagination.
        """
        if status is None:
            return self.get_pending_reminders(page=page, page_size=page_size)

        try:
            status_enum = ReminderStatus(status)
        except ValueError:
            raise ValueError(f"Invalid status: {status}. Must be one of: pending, sent, canceled")

        items = self.reminder_repo.list_by_status(
            status=status_enum,
            page=page,
            page_size=page_size,
        )
        total = self.reminder_repo.count_by_status(status_enum)
        return items, total

    def get_pending_reminders(
        self,
        reference_date: Optional[date] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Reminder], int]:
        """
        Get pending reminders that should be sent on or before reference_date.

        Returns (items, total) for pagination.
        """
        if reference_date is None:
            reference_date = date.today()

        items = self.reminder_repo.list_pending_by_date(
            reference_date=reference_date,
            page=page,
            page_size=page_size,
        )
        total = self.reminder_repo.count_pending_by_date(reference_date)
        return items, total

    def get_reminder(self, reminder_id: int) -> Optional[Reminder]:
        """Get reminder by ID."""
        return self.reminder_repo.get_by_id(reminder_id)

    def mark_sent(self, reminder_id: int) -> Optional[Reminder]:
        """
        Mark reminder as sent.

        Business rules:
        - Can only mark pending reminders as sent
        - Records sent timestamp

        Raises:
            ValueError: If reminder not found or not pending
        """
        reminder = self.reminder_repo.get_by_id(reminder_id)
        if not reminder:
            raise ValueError(f"Reminder {reminder_id} not found")

        if reminder.status != ReminderStatus.PENDING:
            raise ValueError(f"Cannot mark {reminder.status.value} reminder as sent")

        return self.reminder_repo.update_status(
            reminder_id,
            ReminderStatus.SENT,
            sent_at=utcnow(),
        )

    def cancel_reminder(self, reminder_id: int) -> Optional[Reminder]:
        """
        Cancel a pending reminder.

        Business rules:
        - Can only cancel pending reminders
        - Records cancellation timestamp

        Raises:
            ValueError: If reminder not found or not pending
        """
        reminder = self.reminder_repo.get_by_id(reminder_id)
        if not reminder:
            raise ValueError(f"Reminder {reminder_id} not found")

        if reminder.status != ReminderStatus.PENDING:
            raise ValueError(f"Cannot cancel {reminder.status.value} reminder")

        return self.reminder_repo.update_status(
            reminder_id,
            ReminderStatus.CANCELED,
            canceled_at=utcnow(),
        )