from __future__ import annotations

from sqlalchemy.orm import Session

from app.clients.repositories.client_repository import ClientRepository
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.reminders.services import factory, queries, status_changes


class ReminderService:
    """Facade delegating reminder flows to focused modules."""

    def __init__(self, db: Session):
        self.db = db
        self.reminder_repo = ReminderRepository(db)
        self.client_repo = ClientRepository(db)

    # Creation flows
    def create_tax_deadline_reminder(self, **kwargs):
        return factory.create_tax_deadline_reminder(self.reminder_repo, self.client_repo, **kwargs)

    def create_idle_binder_reminder(self, **kwargs):
        return factory.create_idle_binder_reminder(self.reminder_repo, self.client_repo, **kwargs)

    def create_unpaid_charge_reminder(self, **kwargs):
        return factory.create_unpaid_charge_reminder(self.reminder_repo, self.client_repo, **kwargs)

    def create_custom_reminder(self, **kwargs):
        return factory.create_custom_reminder(self.reminder_repo, self.client_repo, **kwargs)

    # Queries
    def get_reminders(self, **kwargs):
        return queries.get_reminders(self.reminder_repo, **kwargs)

    def get_pending_reminders(self, **kwargs):
        return queries.get_pending_reminders(self.reminder_repo, **kwargs)

    def get_reminder(self, reminder_id: int):
        return queries.get_reminder(self.reminder_repo, reminder_id)

    # Status changes
    def mark_sent(self, reminder_id: int):
        return status_changes.mark_sent(self.reminder_repo, reminder_id)

    def cancel_reminder(self, reminder_id: int):
        return status_changes.cancel_reminder(self.reminder_repo, reminder_id)
