from __future__ import annotations

from sqlalchemy.orm import Session

from app.binders.repositories.binder_repository import BinderRepository
from app.businesses.repositories.business_repository import BusinessRepository
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.reminders.schemas.reminders import ReminderCreateRequest
from app.reminders.services import factory as reminder_factory
from app.reminders.services import reminder_queries, request_dispatch, status_changes


class ReminderService:
    def __init__(self, db: Session):
        self.db = db
        self.reminder_repo = ReminderRepository(db)
        self.business_repo = BusinessRepository(db)
        self.client_record_repo = ClientRecordRepository(db)
        self.binder_repo = BinderRepository(db)

    def create_from_request(self, request: ReminderCreateRequest, *, created_by: int):
        return request_dispatch.create_from_request(self, request, created_by=created_by)

    def create_idle_binder_reminder(self, **kwargs):
        return reminder_factory.create_idle_binder_reminder(self.reminder_repo, self.binder_repo, **kwargs)

    def create_document_missing_reminder(self, **kwargs):
        return reminder_factory.create_document_missing_reminder(self.reminder_repo, self.business_repo, **kwargs)

    def create_custom_reminder(self, **kwargs):
        return reminder_factory.create_custom_reminder(self.reminder_repo, self.business_repo, **kwargs)

    def get_reminders(self, **kwargs):
        return reminder_queries.get_reminders(self.reminder_repo, self.business_repo, **kwargs)

    def get_reminders_by_business(self, **kwargs):
        return reminder_queries.get_reminders_by_business(self.reminder_repo, self.business_repo, **kwargs)

    def get_reminders_by_client(self, **kwargs):
        return reminder_queries.get_reminders_by_client(self.reminder_repo, self.business_repo, **kwargs)

    def get_reminder(self, reminder_id: int):
        return reminder_queries.get_reminder(self.reminder_repo, reminder_id)

    def mark_sent(self, reminder_id: int, actor_id: int):
        return status_changes.mark_sent(self.reminder_repo, reminder_id, actor_id=actor_id)

    def cancel_reminder(self, reminder_id: int, actor_id: int):
        return status_changes.cancel_reminder(self.reminder_repo, reminder_id, actor_id=actor_id)
