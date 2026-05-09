from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.binders.repositories.binder_repository import BinderRepository
from app.businesses.repositories.business_repository import BusinessRepository
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.core.exceptions import AppError
from app.reminders.models.reminder import Reminder, ReminderStatus
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.reminders.schemas.reminders import ReminderCreateRequest
from app.reminders.services import (
    factory as reminder_factory,
    request_dispatch,
    status_changes,
)
from app.reminders.services.reminder_context import ReminderContext, build_context_map


class ReminderService:
    def __init__(self, db: Session):
        self.db = db
        self.reminder_repo = ReminderRepository(db)
        self.business_repo = BusinessRepository(db)
        self.client_record_repo = ClientRecordRepository(db)
        self.binder_repo = BinderRepository(db)

    def create_from_request(self, request: ReminderCreateRequest, *, created_by: int):
        return request_dispatch.create_from_request(
            self, request, created_by=created_by
        )

    def create_idle_binder_reminder(self, **kwargs):
        return reminder_factory.create_idle_binder_reminder(
            self.reminder_repo, self.binder_repo, **kwargs
        )

    def create_document_missing_reminder(self, **kwargs):
        return reminder_factory.create_document_missing_reminder(
            self.reminder_repo, self.business_repo, **kwargs
        )

    def create_custom_reminder(self, **kwargs):
        return reminder_factory.create_custom_reminder(
            self.reminder_repo, self.business_repo, **kwargs
        )

    def get_reminders(
        self,
        *,
        status: Optional[str] = None,
        created_before: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Reminder], int, dict[int, ReminderContext]]:
        if status is None:
            status = ReminderStatus.PENDING.value
        valid_statuses = {e.value for e in ReminderStatus}
        if status not in valid_statuses:
            raise AppError(
                f"סטטוס לא חוקי: {status}. חייב להיות אחד מהבאים: {', '.join(valid_statuses)}",
                "REMINDER.INVALID_STATUS",
            )
        status_enum = ReminderStatus(status)
        items = self.reminder_repo.list_by_status(
            status=status_enum,
            page=page,
            page_size=page_size,
            created_before=created_before,
        )
        total = self.reminder_repo.count_by_status(
            status_enum, created_before=created_before
        )
        return items, total, build_context_map(self.db, self.business_repo, items)

    def get_reminders_by_business(
        self, *, business_id: int, page: int = 1, page_size: int = 20
    ) -> tuple[list[Reminder], int, dict[int, ReminderContext]]:
        items = self.reminder_repo.list_by_business(
            business_id=business_id, page=page, page_size=page_size
        )
        total = self.reminder_repo.count_by_business(business_id)
        return items, total, build_context_map(self.db, self.business_repo, items)

    def get_reminders_by_client(
        self, *, client_record_id: int, page: int = 1, page_size: int = 20
    ) -> tuple[list[Reminder], int, dict[int, ReminderContext]]:
        client_record_id = int(
            ClientRecordRepository(self.db).get_by_id(client_record_id).id
        )
        items = self.reminder_repo.list_by_client_record(
            client_record_id, page=page, page_size=page_size
        )
        total = self.reminder_repo.count_by_client_record(client_record_id)
        return items, total, build_context_map(self.db, self.business_repo, items)

    def get_reminder(self, reminder_id: int) -> Optional[Reminder]:
        return self.reminder_repo.get_by_id(reminder_id)

    def mark_sent(self, reminder_id: int, actor_id: int):
        return status_changes.mark_sent(
            self.reminder_repo, reminder_id, actor_id=actor_id
        )

    def cancel_reminder(self, reminder_id: int, actor_id: int):
        return status_changes.cancel_reminder(
            self.reminder_repo, reminder_id, actor_id=actor_id
        )
