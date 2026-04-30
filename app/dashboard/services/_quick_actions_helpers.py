"""Per-category builders for dashboard quick actions."""
from __future__ import annotations

import datetime as _dt
from datetime import date, timezone
from typing import Optional

from app.actions.action_helpers import build_action, build_confirm
from app.annual_reports.models.annual_report_enums import AnnualReportStatus
from app.annual_reports.repositories.annual_report_repository import AnnualReportRepository
from app.annual_reports.repositories.report_lifecycle_repository import DASHBOARD_FINAL_STATUSES
from app.binders.repositories.binder_repository import BinderRepository
from app.businesses.repositories.business_repository import BusinessRepository
from app.clients.repositories.client_record_read_repository import get_full_record
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.notification.models.notification import NotificationTrigger
from app.notification.repositories.notification_repository import NotificationRepository
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository

_MONTH_HE = {
    1: "ינואר", 2: "פברואר", 3: "מרץ", 4: "אפריל",
    5: "מאי", 6: "יוני", 7: "יולי", 8: "אוגוסט",
    9: "ספטמבר", 10: "אוקטובר", 11: "נובמבר", 12: "דצמבר",
}
_ANNUAL_STATUS_LABEL_HE = {
    AnnualReportStatus.NOT_STARTED: "טרם החל",
    AnnualReportStatus.COLLECTING_DOCS: "איסוף מסמכים",
    AnnualReportStatus.DOCS_COMPLETE: "מסמכים מלאים",
    AnnualReportStatus.IN_PREPARATION: "בהכנה",
    AnnualReportStatus.PENDING_CLIENT: "ממתין לאישור לקוח",
    AnnualReportStatus.AMENDED: "בתיקון",
    AnnualReportStatus.ASSESSMENT_ISSUED: "שומה הוצאה",
    AnnualReportStatus.OBJECTION_FILED: "השגה הוגשה",
}
_VAT_STATUS_LABEL_HE = {
    VatWorkItemStatus.PENDING_MATERIALS: "ממתין לחומרים",
    VatWorkItemStatus.MATERIAL_RECEIVED: "חומרים התקבלו",
    VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS: "בהזנת נתונים",
    VatWorkItemStatus.READY_FOR_REVIEW: "מוכן לבדיקה",
    VatWorkItemStatus.FILED: "הוגש",
    VatWorkItemStatus.CANCELED: "בוטל",
    VatWorkItemStatus.ARCHIVED: "בארכיון",
}

CATEGORY_ORDER = {"vat": 0, "annual_reports": 1, "binders": 2}

_BINDER_PICKUP_OVERDUE_DAYS = 30
_BINDER_REMINDER_COOLDOWN_DAYS = 5
_ANNUAL_PENDING_CLIENT_DAYS = 3
_ANNUAL_REMINDER_COOLDOWN_DAYS = 2
_UPCOMING_WINDOW_DAYS = 7
_VAT_UPCOMING_DAY_OF_MONTH = 8  # show upcoming from day 8 (7 days before deadline on 15th)
try:
    from tax_rules.registry import get_vat_statutory_deadline_day as _get_stat_day
    _VAT_DEADLINE_DAY: int = _get_stat_day(_dt.date.today().year)
except Exception:
    _VAT_DEADLINE_DAY = 15


def _period_label(period: str) -> str:
    try:
        year, month = period.split("-")
        return f"{_MONTH_HE.get(int(month), month)} {year}"
    except Exception:
        return period


def _vat_due_label(period: str, urgency: str, days: int) -> str:
    status = f"באיחור {days} ימים" if urgency == "overdue" else f"עוד {days} ימים"
    return f"דוח מע״מ · {_period_label(period)} · {status}"


def _vat_status_label(status) -> str:
    if status is None:
        return "סטטוס עבודה לא ידוע"
    return _VAT_STATUS_LABEL_HE.get(status, str(getattr(status, "value", status)))


def _enrich(action: dict, category: str, urgency: str, due_date: date, due_label: str) -> dict:
    action["category"] = category
    action["urgency"] = urgency
    action["due_date"] = due_date.isoformat()
    action["due_label"] = due_label
    return action


def _client_name(db, client_record_id: int, business_repo: BusinessRepository) -> Optional[str]:
    record = ClientRecordRepository(business_repo.db).get_by_id(client_record_id)
    if not record:
        return None
    client = get_full_record(db, client_record_id)
    return client["full_name"] if client else None


def build_vat_actions(
    vat_repo: VatWorkItemRepository,
    business_repo: BusinessRepository,
    today: date,
) -> list[dict]:
    current_period = today.strftime("%Y-%m")
    items = vat_repo.list_open_up_to_period(current_period)
    result: list[dict] = []

    for item in items:
        year, month = item.period.split("-")
        deadline = date(int(year), int(month), _VAT_DEADLINE_DAY)

        if deadline < today:
            urgency = "overdue"
            days_overdue = (today - deadline).days
            due_label = _vat_due_label(item.period, urgency, days_overdue)
        elif today.day >= _VAT_UPCOMING_DAY_OF_MONTH and item.period == current_period:
            urgency = "upcoming"
            days_left = (deadline - today).days
            due_label = _vat_due_label(item.period, urgency, days_left)
        else:
            continue

        client_name = _client_name(business_repo.db, item.client_record_id, business_repo)
        action = build_action(
            key="vat_navigate",
            label='פתח דוח מע"מ',
            method="get",
            endpoint=f"/clients/{item.client_record_id}/vat",
            action_id=f"vat-{item.id}-navigate",
        )
        action["client_name"] = client_name
        action["description"] = _vat_status_label(getattr(item, "status", None))
        _enrich(action, "vat", urgency, deadline, due_label)
        result.append(action)

    return result


def build_annual_report_actions(
    annual_report_repo: AnnualReportRepository,
    business_repo: BusinessRepository,
    notification_repo: NotificationRepository,
    today: date,
) -> list[dict]:
    reports = annual_report_repo.list_for_dashboard()
    now_utc = _dt.datetime.now(timezone.utc)
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

        client_name = _client_name(business_repo.db, report.client_record_id, business_repo)

        is_pending_client = report.status == AnnualReportStatus.PENDING_CLIENT
        pending_days = 0
        if is_pending_client:
            pending_days = (now_utc - report.updated_at.replace(tzinfo=timezone.utc)).days

        if is_pending_client and pending_days >= _ANNUAL_PENDING_CLIENT_DAYS:
            last_reminder = notification_repo.get_last_for_annual_report_trigger(
                report.id, NotificationTrigger.ANNUAL_REPORT_CLIENT_REMINDER
            )
            cooldown_ok = (
                not last_reminder or
                (now_utc - last_reminder.created_at.replace(tzinfo=timezone.utc)).days >= _ANNUAL_REMINDER_COOLDOWN_DAYS
            )
            if cooldown_ok:
                action = build_action(
                    key="annual_report_client_reminder",
                    label="שלח תזכורת לאישור",
                    method="post",
                    endpoint=f"/api/v1/annual-reports/{report.id}/client-reminder",
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

        status_label = _ANNUAL_STATUS_LABEL_HE.get(report.status, str(report.status))
        action = build_action(
            key="annual_report_navigate",
            label="פתח דוח שנתי",
            method="get",
            endpoint=f"/tax/reports/{report.id}",
            action_id=f"annual-{report.id}-navigate",
        )
        action["client_name"] = client_name
        _enrich(action, "annual_reports", urgency, deadline, f"{status_label} · {due_label}")
        result.append(action)

    return result


def build_binder_actions(
    binder_repo: BinderRepository,
    business_repo: BusinessRepository,
    notification_repo: NotificationRepository,
) -> list[dict]:
    binders = binder_repo.list_overdue_pickup(_BINDER_PICKUP_OVERDUE_DAYS)
    now_utc = _dt.datetime.now(timezone.utc)
    result: list[dict] = []

    for binder in binders:
        last_reminder = notification_repo.get_last_for_binder_trigger(
            binder.id, NotificationTrigger.PICKUP_REMINDER
        )
        if last_reminder:
            days_since = (now_utc - last_reminder.created_at.replace(tzinfo=timezone.utc)).days
            if days_since < _BINDER_REMINDER_COOLDOWN_DAYS:
                continue

        record = ClientRecordRepository(business_repo.db).get_by_id(binder.client_record_id)
        businesses = business_repo.list_by_legal_entity(record.legal_entity_id, page=1, page_size=1) if record else []
        business = businesses[0] if businesses else None
        client_name = business.full_name if business else None

        days_waiting = int((now_utc - binder.ready_for_pickup_at.replace(tzinfo=timezone.utc)).days)
        due_date = binder.ready_for_pickup_at.date()
        due_label = f"ממתין לאיסוף {days_waiting} ימים"

        action = build_action(
            key="binder_pickup_reminder",
            label="שלח תזכורת איסוף",
            method="post",
            endpoint=f"/api/v1/binders/{binder.id}/pickup-reminder",
            action_id=f"binder-{binder.id}-pickup-reminder",
            confirm=build_confirm(
                title="שליחת תזכורת איסוף",
                message=f"לשלוח תזכורת ל{client_name or 'לקוח'} לאסוף את קלסר {binder.binder_number}?",
                confirm_label="שלח",
            ),
        )
        action["client_name"] = client_name
        action["binder_number"] = binder.binder_number
        _enrich(action, "binders", "overdue", due_date, due_label)
        result.append(action)

    return result
