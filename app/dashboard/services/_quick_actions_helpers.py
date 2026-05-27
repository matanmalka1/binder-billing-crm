"""Per-category builders for dashboard quick actions."""

from __future__ import annotations

import datetime as _dt
from datetime import date

from app.actions.action_helpers import build_action, build_confirm
from app.annual_reports.models.annual_report_enums import AnnualReportStatus
from app.annual_reports.repositories.annual_report_repository import (
    AnnualReportRepository,
)
from app.binders.repositories.binder_repository import BinderRepository
from app.businesses.repositories.business_repository import BusinessRepository
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.repositories.legal_entity_repository import LegalEntityRepository
from app.notification.models.notification import NotificationTrigger
from app.notification.repositories.notification_repository import NotificationRepository
from app.notification.services.constants import (
    ANNUAL_REMINDER_COOLDOWN_DAYS,
    HANDOVER_REMINDER_COOLDOWN_DAYS,
)

CATEGORY_ORDER = {"annual_reports": 1, "binders": 2}

_BINDER_HANDOVER_OVERDUE_DAYS = 30
_ANNUAL_PENDING_CLIENT_DAYS = 3
_UPCOMING_WINDOW_DAYS = 14


def _enrich(action: dict, category: str, urgency: str, due_date: date, due_label: str) -> dict:
    action["category"] = category
    action["urgency"] = urgency
    action["due_date"] = due_date.isoformat()
    action["due_label"] = due_label
    return action


def _batch_client_names(db, client_record_ids: list[int]) -> dict[int, str | None]:
    """Batch-load client display names by client record IDs (avoids N+1)."""
    if not client_record_ids:
        return {}
    unique_ids = list(set(client_record_ids))
    client_record_repo = ClientRecordRepository(db)
    legal_entity_repo = LegalEntityRepository(db)
    records = client_record_repo.list_by_ids(unique_ids)
    legal_entity_ids = list({r.legal_entity_id for r in records if r.legal_entity_id})
    entities = legal_entity_repo.list_by_ids(legal_entity_ids)
    entity_name_map = {e.id: e.official_name for e in entities}
    return {r.id: entity_name_map.get(r.legal_entity_id) for r in records}


def build_annual_report_actions(
    annual_report_repo: AnnualReportRepository,
    business_repo: BusinessRepository,
    notification_repo: NotificationRepository,
    today: date,
) -> list[dict]:
    reports = annual_report_repo.list_for_dashboard()
    if not reports:
        return []

    now_utc = _dt.datetime.now(_dt.UTC)
    client_record_ids = [r.client_record_id for r in reports if r.client_record_id]
    client_name_map = _batch_client_names(business_repo.db, client_record_ids)
    last_reminders = notification_repo.latest_by_annual_report_ids(
        [r.id for r in reports], NotificationTrigger.ANNUAL_REPORT_CLIENT_REMINDER
    )

    result: list[dict] = []
    for report in reports:
        deadline_dt = report.filing_deadline
        if not deadline_dt:
            continue
        deadline = deadline_dt.date() if hasattr(deadline_dt, "date") else deadline_dt
        days_to_deadline = (deadline - today).days

        if days_to_deadline < 0:
            urgency = "overdue"
            days_overdue = abs(days_to_deadline)
            due_label = f"באיחור של {days_overdue} ימים · {report.tax_year}"
        elif days_to_deadline <= _UPCOMING_WINDOW_DAYS:
            urgency = "upcoming"
            due_label = f"{days_to_deadline} ימים לדדליין · {report.tax_year}"
        else:
            continue

        client_name = client_name_map.get(report.client_record_id)

        is_pending_client = report.status == AnnualReportStatus.PENDING_CLIENT
        pending_days = 0
        if is_pending_client:
            pending_days = (now_utc - report.updated_at.replace(tzinfo=_dt.UTC)).days

        if is_pending_client and pending_days >= _ANNUAL_PENDING_CLIENT_DAYS:
            last_reminder = last_reminders.get(report.id)
            cooldown_ok = (
                not last_reminder
                or (now_utc - last_reminder.created_at.replace(tzinfo=_dt.UTC)).days
                >= ANNUAL_REMINDER_COOLDOWN_DAYS
            )
            if cooldown_ok:
                action = build_action(
                    key="annual_report_client_reminder",
                    label="שלח תזכורת לאישור",
                    method="post",
                    endpoint=f"/annual-reports/{report.id}/client-reminder",
                    action_id=f"annual-{report.id}-reminder",
                    confirm=build_confirm(
                        title="שליחת תזכורת ללקוח",
                        message=f"לשלוח תזכורת ל{client_name or 'לקוח'} לאישור הדוח השנתי לשנת {report.tax_year}?",
                        confirm_label="שלח",
                    ),
                )
                action["client_name"] = client_name
                _enrich(action, "annual_reports", urgency, deadline, due_label)
                result.append(action)
                continue

    return result


def build_binder_actions(
    binder_repo: BinderRepository,
    business_repo: BusinessRepository,
    notification_repo: NotificationRepository,
) -> list[dict]:
    binders = binder_repo.list_overdue_handover(_BINDER_HANDOVER_OVERDUE_DAYS)
    if not binders:
        return []

    now_utc = _dt.datetime.now(_dt.UTC)
    client_record_ids = [b.client_record_id for b in binders if b.client_record_id]
    client_name_map = _batch_client_names(business_repo.db, client_record_ids)
    last_reminders = notification_repo.latest_by_binder_ids(
        [b.id for b in binders], NotificationTrigger.BINDER_GENERAL_REMINDER
    )

    result: list[dict] = []
    for binder in binders:
        last_reminder = last_reminders.get(binder.id)
        if last_reminder:
            days_since = (now_utc - last_reminder.created_at.replace(tzinfo=_dt.UTC)).days
            if days_since < HANDOVER_REMINDER_COOLDOWN_DAYS:
                continue

        client_name = client_name_map.get(binder.client_record_id)

        days_waiting = int((now_utc - binder.ready_for_handover_at.replace(tzinfo=_dt.UTC)).days)
        due_date = binder.ready_for_handover_at.date()
        due_label = f"ממתין למסירה {days_waiting} ימים"

        action = build_action(
            key="binder_handover_reminder",
            label="שלח תזכורת מסירה",
            method="post",
            endpoint=f"/binders/{binder.id}/handover-reminder",
            action_id=f"binder-{binder.id}-handover-reminder",
            confirm=build_confirm(
                title="שליחת תזכורת מסירה",
                message=f"לשלוח תזכורת ל{client_name or 'לקוח'} למסירת קלסר {binder.binder_number}?",
                confirm_label="שלח",
            ),
        )
        action["client_name"] = client_name
        action["binder_number"] = binder.binder_number
        _enrich(action, "binders", "overdue", due_date, due_label)
        result.append(action)

    return result
