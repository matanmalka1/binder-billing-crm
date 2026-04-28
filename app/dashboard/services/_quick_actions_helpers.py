"""Shared helpers and per-category builders for dashboard quick actions."""

from __future__ import annotations

import datetime as _dt
from datetime import date, timezone
from typing import Optional

from app.actions.action_contracts import build_action, get_binder_actions
from app.annual_reports.models.annual_report_enums import AnnualReportStatus
from app.annual_reports.repositories.annual_report_repository import AnnualReportRepository
from app.binders.models.binder import BinderStatus
from app.binders.repositories.binder_repository import BinderRepository
from app.clients.repositories.client_record_read_repository import get_full_record
from app.businesses.repositories.business_repository import BusinessRepository
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository

_MONTH_HE = {
    1: "ינואר", 2: "פברואר", 3: "מרץ", 4: "אפריל",
    5: "מאי", 6: "יוני", 7: "יולי", 8: "אוגוסט",
    9: "ספטמבר", 10: "אוקטובר", 11: "נובמבר", 12: "דצמבר",
}
_STATUS_LABEL_HE = {
    AnnualReportStatus.PENDING_CLIENT: "ממתין לאישור לקוח",
    AnnualReportStatus.COLLECTING_DOCS: "מאסף מסמכים",
}

CATEGORY_ORDER = {"binders": 0, "vat": 1, "annual_reports": 2}


def enrich(action: dict, category: str, due_label: Optional[str] = None) -> dict:
    action["category"] = category
    if due_label:
        action["due_label"] = due_label
    return action


def period_label(period: str) -> str:
    """Convert '2026-01' → 'ינואר 2026'."""
    try:
        year, month = period.split("-")
        return f"{_MONTH_HE.get(int(month), month)} {year}"
    except Exception:
        return period


def days_since(d: date) -> int:
    return max(0, (date.today() - d).days)


def build_binder_actions(binder_repo: BinderRepository, business_repo: BusinessRepository) -> list[dict]:
    """Return only overdue binder quick actions."""
    binders = binder_repo.list_active()
    overdue_ready = overdue_return = None

    for binder in binders:
        binder_acts = get_binder_actions(binder)
        d = days_since(binder.period_start) if binder.period_start else 0
        if d <= 90:
            continue

        if binder.status in (BinderStatus.IN_OFFICE, BinderStatus.IN_OFFICE.value):
            act = next((a for a in binder_acts if a["key"] == "ready"), None)
            if act and overdue_ready is None:
                overdue_ready = (binder, act, d)

        if binder.status in (BinderStatus.READY_FOR_PICKUP, BinderStatus.READY_FOR_PICKUP.value):
            act = next((a for a in binder_acts if a["key"] == "return"), None)
            if act and overdue_return is None:
                overdue_return = (binder, act, d)

        if overdue_ready and overdue_return:
            break

    result: list[dict] = []
    for candidate in [overdue_ready, overdue_return]:
        if candidate is None:
            continue
        binder, action, d = candidate
        record = ClientRecordRepository(business_repo.db).get_by_id(binder.client_record_id)
        businesses = business_repo.list_by_legal_entity(record.legal_entity_id, page=1, page_size=1) if record else []
        business = businesses[0] if businesses else None
        action["client_name"] = business.full_name if business else None
        action["binder_number"] = binder.binder_number
        label = f"פג תוקף לפני {d - 90} ימים"
        enrich(action, "binders", label)
        result.append(action)
    return result


def build_vat_actions(
    vat_repo: VatWorkItemRepository,
    business_repo: BusinessRepository,
    current_period: str,
) -> list[dict]:
    items = vat_repo.list_not_filed_for_period(current_period, limit=3)
    plabel = period_label(current_period)
    cr_repo = ClientRecordRepository(business_repo.db)
    result: list[dict] = []
    for item in items:
        record = cr_repo.get_by_id(item.client_record_id)
        if not record:
            continue
        client = get_full_record(business_repo.db, item.client_record_id)
        action = build_action(
            key="vat_navigate",
            label='פתח דוח מע"מ',
            method="get",
            endpoint=f"/client-records/{item.client_record_id}/vat",
            action_id=f"vat-{item.id}-navigate",
        )
        action["client_name"] = client["full_name"] if client else None
        enrich(action, "vat", f"תקופה: {plabel}")
        result.append(action)
    return result


def build_annual_report_actions(
    annual_report_repo: AnnualReportRepository,
    business_repo: BusinessRepository,
) -> list[dict]:
    stuck = annual_report_repo.list_stuck_reports(stale_days=7, limit=3)
    cr_repo = ClientRecordRepository(business_repo.db)
    result: list[dict] = []
    for report in stuck:
        record = cr_repo.get_by_id(report.client_record_id)
        if not record:
            continue
        businesses = business_repo.list_by_legal_entity(record.legal_entity_id, page=1, page_size=1)
        business = businesses[0] if businesses else None
        status_label = _STATUS_LABEL_HE.get(report.status, str(report.status))
        updated = report.updated_at.replace(tzinfo=timezone.utc)
        stale_days = (_dt.datetime.now(timezone.utc) - updated).days
        action = build_action(
            key="annual_report_navigate",
            label="פתח דוח שנתי",
            method="get",
            endpoint=f"/client-records/{report.client_record_id}/annual-reports",
            action_id=f"annual-{report.id}-navigate",
        )
        action["client_name"] = business.full_name if business else None
        enrich(action, "annual_reports", f"{status_label} · {stale_days} ימים")
        result.append(action)
    return result
