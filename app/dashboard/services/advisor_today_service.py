from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.businesses.repositories.business_repository import BusinessRepository
from app.reminders.models.reminder import ReminderStatus, ReminderType
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.reminders.services.reminder_context import build_context_map
from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadline, TaxDeadlineStatus
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository

_UPCOMING_DEADLINE_DAYS = 30
_STALE_REMINDER_DAYS = 7
_REMINDER_PREVIEW_LENGTH = 48
_REMINDER_FETCH_LIMIT = 50
_DEDUPED_REMINDER_TYPES = {ReminderType.UNPAID_CHARGE}

_DEADLINE_COPY = {
    DeadlineType.VAT: ("מע״מ", "הגשה ותשלום"),
    DeadlineType.ADVANCE_PAYMENT: ("מס הכנסה", "תשלום מקדמות"),
    DeadlineType.NATIONAL_INSURANCE: ("ביטוח לאומי", "תשלום מקדמות"),
    DeadlineType.ANNUAL_REPORT: ("דוחות שנתיים", "הגשה"),
}


class AdvisorTodayService:
    def __init__(self, db: Session):
        self.db = db
        self.business_repo = BusinessRepository(db)
        self.reminder_repo = ReminderRepository(db)
        self.tax_deadline_repo = TaxDeadlineRepository(db)

    def build(self, reference_date: date) -> dict:
        return {
            "deadline_items": self._deadline_items(reference_date),
            "reminder_items": self._reminder_items(reference_date),
        }

    def _deadline_items(self, reference_date: date) -> list[dict]:
        due_to = reference_date + timedelta(days=_UPCOMING_DEADLINE_DAYS)
        rows = (
            self.db.query(
                TaxDeadline.deadline_type,
                TaxDeadline.due_date,
                func.min(TaxDeadline.period).label("period"),
                func.max(TaxDeadline.period).label("max_period"),
                func.min(TaxDeadline.tax_year).label("tax_year"),
                func.count(func.distinct(TaxDeadline.client_record_id)).label("client_count"),
                func.min(TaxDeadline.id).label("first_id"),
            )
            .filter(
                TaxDeadline.deleted_at.is_(None),
                TaxDeadline.status == TaxDeadlineStatus.PENDING,
                TaxDeadline.due_date >= reference_date,
                TaxDeadline.due_date <= due_to,
            )
            .group_by(TaxDeadline.deadline_type, TaxDeadline.due_date)
            .order_by(TaxDeadline.due_date.asc(), TaxDeadline.deadline_type.asc())
            .all()
        )
        return [self._deadline_item(row, reference_date) for row in rows if row.deadline_type in _DEADLINE_COPY]

    def _reminder_items(self, reference_date: date) -> list[dict]:
        created_before = datetime.combine(reference_date - timedelta(days=_STALE_REMINDER_DAYS), datetime.max.time())
        reminders = self.reminder_repo.list_by_status(
            ReminderStatus.PENDING,
            page=1,
            page_size=_REMINDER_FETCH_LIMIT,
            created_before=created_before,
        )
        reminders = [r for r in reminders if r.reminder_type not in _DEDUPED_REMINDER_TYPES]
        context = build_context_map(self.db, self.business_repo, reminders, self.tax_deadline_repo)
        return [
            _reminder_item(reminder, context.get(reminder.id, {}))
            for reminder in reminders
        ]

    def _deadline_item(self, row, reference_date: date) -> dict:
        title, action = _DEADLINE_COPY[row.deadline_type]
        due_date = row.due_date
        period_label = _period_label(row.deadline_type, row.period, row.max_period, row.tax_year)
        description_parts = [f"{int(row.client_count)} לקוחות רלוונטיים"]
        if period_label:
            description_parts.append(period_label)
        return {
            "id": row.first_id,
            "label": title,
            "sublabel": f"{action} עד {_format_date(due_date)} · {_days_label(due_date, reference_date)}",
            "description": " · ".join(description_parts),
            "href": "/tax/deadlines",
        }


def _format_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")


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


def _period_label(
    deadline_type: DeadlineType,
    period: str | None,
    max_period: str | None,
    tax_year: int | None,
) -> str | None:
    if deadline_type == DeadlineType.ANNUAL_REPORT:
        return f"שנת מס {tax_year}" if tax_year else None
    if not period:
        return None
    if max_period and max_period != period:
        return None
    return f"תקופת מועד {_format_period(period)}"


def _format_period(period: str) -> str:
    try:
        year, month = period.split("-")
    except ValueError:
        return period
    return f"{month}/{year}"


def _days_label(due_date: date, reference_date: date) -> str:
    days = (due_date - reference_date).days
    if days < 0:
        return f"באיחור {abs(days)} ימים"
    if days == 0:
        return "היום"
    return f"עוד {days} ימים"
