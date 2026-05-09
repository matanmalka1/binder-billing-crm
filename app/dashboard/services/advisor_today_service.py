from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.businesses.repositories.business_repository import BusinessRepository
from app.reminders.models.reminder import ReminderStatus
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.reminders.services.reminder_context import build_context_map


_STALE_REMINDER_DAYS = 7
_REMINDER_PREVIEW_LENGTH = 48
_REMINDER_FETCH_LIMIT = 50


class AdvisorTodayService:
    def __init__(self, db: Session):
        self.db = db
        self.business_repo = BusinessRepository(db)
        self.reminder_repo = ReminderRepository(db)

    def build(self, reference_date: date) -> dict:
        return {
            "deadline_items": [],
            "reminder_items": self._reminder_items(reference_date),
        }

    def _reminder_items(self, reference_date: date) -> list[dict]:
        created_before = datetime.combine(
            reference_date - timedelta(days=_STALE_REMINDER_DAYS), datetime.max.time()
        )
        reminders = self.reminder_repo.list_by_status(
            ReminderStatus.PENDING,
            page=1,
            page_size=_REMINDER_FETCH_LIMIT,
            created_before=created_before,
        )
        context = build_context_map(self.db, self.business_repo, reminders)
        return [
            _reminder_item(reminder, context.get(reminder.id, {}))
            for reminder in reminders
        ]


def _reminder_item(reminder, context: dict) -> dict:
    business_name = context.get("business_name") or f"עסק #{reminder.business_id}"
    return {
        "id": reminder.id,
        "label": context.get("client_name") or f"לקוח #{reminder.client_record_id}",
        "sublabel": f"{business_name} · {_clean_reminder_message(reminder.message)}",
        "href": "/reminders",
    }


def _clean_reminder_message(message: str) -> str:
    cleaned = message.removeprefix("תזכורת:").strip()
    return cleaned[:_REMINDER_PREVIEW_LENGTH]
