from __future__ import annotations

from sqlalchemy.orm import Session

from app.binders.repositories.binder_repository import BinderRepository
from app.charge.repositories.charge_repository import ChargeRepository
from app.clients.repositories.client_repository import ClientRepository
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.reminders.services import factory, reminder_queries, status_changes
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository


class ReminderService:
    """Facade delegating reminder flows to focused modules."""

    def __init__(self, db: Session):
        self.db = db
        self.reminder_repo = ReminderRepository(db)
        self.client_repo = ClientRepository(db)
        self.charge_repo = ChargeRepository(db)
        self.binder_repo = BinderRepository(db)
        self.tax_deadline_repo = TaxDeadlineRepository(db)

    # Creation flows
    def create_tax_deadline_reminder(self, **kwargs):
        return factory.create_tax_deadline_reminder(
            self.reminder_repo, self.client_repo, self.tax_deadline_repo, **kwargs
        )

    def create_idle_binder_reminder(self, **kwargs):
        return factory.create_idle_binder_reminder(
            self.reminder_repo, self.client_repo, self.binder_repo, **kwargs
        )

    def create_unpaid_charge_reminder(self, **kwargs):
        return factory.create_unpaid_charge_reminder(
            self.reminder_repo, self.client_repo, self.charge_repo, **kwargs
        )

    def create_custom_reminder(self, **kwargs):
        return factory.create_custom_reminder(self.reminder_repo, self.client_repo, **kwargs)

    # Queries
    def get_reminders(self, **kwargs):
        return reminder_queries.get_reminders(self.reminder_repo, self.client_repo, **kwargs)

    def get_pending_reminders(self, **kwargs):
        return reminder_queries.get_pending_reminders(self.reminder_repo, self.client_repo, **kwargs)

    def get_reminders_by_client(self, **kwargs):
        return reminder_queries.get_reminders_by_client(self.reminder_repo, self.client_repo, **kwargs)

    def get_reminder(self, reminder_id: int):
        return reminder_queries.get_reminder(self.reminder_repo, reminder_id)

    # Status changes
    def mark_sent(self, reminder_id: int):
        return status_changes.mark_sent(self.reminder_repo, reminder_id)

    def cancel_reminder(self, reminder_id: int):
        return status_changes.cancel_reminder(self.reminder_repo, reminder_id)
