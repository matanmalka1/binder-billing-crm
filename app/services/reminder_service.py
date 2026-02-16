from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.reminder import Reminder, ReminderStatus, ReminderType
from app.repositories.client_repository import ClientRepository


class ReminderService:
    """
    Proactive reminder management.
    
    Handles:
    - Tax deadline reminders (X days before due date)
    - Idle binder reminders (X days without activity)
    - Unpaid charge reminders (X days after issue date)
    """

    def __init__(self, db: Session):
        self.db = db
        self.client_repo = ClientRepository(db)

    def create_tax_deadline_reminder(
        self,
        client_id: int,
        tax_deadline_id: int,
        target_date: date,
        days_before: int,
        message: Optional[str] = None,
    ) -> Reminder:
        """Create reminder for tax deadline."""
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise ValueError(f"Client {client_id} not found")

        send_on = target_date - timedelta(days=days_before)
        
        if message is None:
            message = f"תזכורת: מועד מס בעוד {days_before} ימים ({target_date})"

        reminder = Reminder(
            client_id=client_id,
            reminder_type=ReminderType.TAX_DEADLINE_APPROACHING,
            target_date=target_date,
            days_before=days_before,
            send_on=send_on,
            tax_deadline_id=tax_deadline_id,
            message=message,
            status=ReminderStatus.PENDING,
        )

        self.db.add(reminder)
        self.db.commit()
        self.db.refresh(reminder)
        return reminder

    def create_idle_binder_reminder(
        self,
        client_id: int,
        binder_id: int,
        days_idle: int,
        message: Optional[str] = None,
    ) -> Reminder:
        """Create reminder for idle binder."""
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise ValueError(f"Client {client_id} not found")

        target_date = date.today() + timedelta(days=days_idle)
        send_on = date.today()
        
        if message is None:
            message = f"תזכורת: תיק לא טופל {days_idle} ימים"

        reminder = Reminder(
            client_id=client_id,
            reminder_type=ReminderType.BINDER_IDLE,
            target_date=target_date,
            days_before=0,
            send_on=send_on,
            binder_id=binder_id,
            message=message,
            status=ReminderStatus.PENDING,
        )

        self.db.add(reminder)
        self.db.commit()
        self.db.refresh(reminder)
        return reminder

    def create_unpaid_charge_reminder(
        self,
        client_id: int,
        charge_id: int,
        days_unpaid: int,
        message: Optional[str] = None,
    ) -> Reminder:
        """Create reminder for unpaid charge."""
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise ValueError(f"Client {client_id} not found")

        target_date = date.today()
        send_on = date.today()
        
        if message is None:
            message = f"תזכורת: חשבונית לא שולמה {days_unpaid} ימים"

        reminder = Reminder(
            client_id=client_id,
            reminder_type=ReminderType.UNPAID_CHARGE,
            target_date=target_date,
            days_before=0,
            send_on=send_on,
            charge_id=charge_id,
            message=message,
            status=ReminderStatus.PENDING,
        )

        self.db.add(reminder)
        self.db.commit()
        self.db.refresh(reminder)
        return reminder

    def get_pending_reminders(
        self,
        reference_date: Optional[date] = None,
    ) -> list[Reminder]:
        """Get all pending reminders that should be sent today or earlier."""
        if reference_date is None:
            reference_date = date.today()

        return (
            self.db.query(Reminder)
            .filter(
                Reminder.status == ReminderStatus.PENDING,
                Reminder.send_on <= reference_date,
            )
            .order_by(Reminder.send_on.asc())
            .all()
        )

    def mark_sent(self, reminder_id: int) -> Optional[Reminder]:
        """Mark reminder as sent."""
        from app.utils.time import utcnow
        
        reminder = self.db.query(Reminder).filter(Reminder.id == reminder_id).first()
        if not reminder:
            return None

        reminder.status = ReminderStatus.SENT
        reminder.sent_at = utcnow()
        self.db.commit()
        self.db.refresh(reminder)
        return reminder

    def cancel_reminder(self, reminder_id: int) -> Optional[Reminder]:
        """Cancel a pending reminder."""
        from app.utils.time import utcnow
        
        reminder = self.db.query(Reminder).filter(Reminder.id == reminder_id).first()
        if not reminder:
            return None

        reminder.status = ReminderStatus.CANCELED
        reminder.canceled_at = utcnow()
        self.db.commit()
        self.db.refresh(reminder)
        return reminder