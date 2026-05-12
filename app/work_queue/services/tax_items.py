from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select

from app.annual_reports import models as annual_report_models
from app.clients.repositories.active_client_scope import scope_to_active_clients_stmt
from app.vat_reports.repositories.vat_compliance_repository import (
    VatComplianceRepository,
)
from app.work_queue.schemas.work_queue import WorkQueueItem, WorkQueueSourceType
from app.work_queue.services.common import UPCOMING_WINDOW_DAYS, WorkQueueContext
from app.work_queue.services.payloads import (
    annual_report_payload,
    vat_work_item_payload,
)

_DONE_ANNUAL_STATUSES = {
    annual_report_models.AnnualReportStatus.CLOSED,
    annual_report_models.AnnualReportStatus.CANCELED,
    annual_report_models.AnnualReportStatus.ACCEPTED,
}


def _vat_due_date(item) -> date:
    due_date_effective = item.due_date_effective
    if due_date_effective is None:
        raise ValueError(f"VatWorkItem {item.id} is missing due_date_effective")
    return (
        due_date_effective.date()
        if hasattr(due_date_effective, "date")
        else due_date_effective
    )


def vat_filing_items(
    ctx: WorkQueueContext, client_record_id: Optional[int]
) -> list[WorkQueueItem]:
    """Return work-queue items for unfiled VAT periods.

    get_overdue_unfiled returns full VatWorkItem objects — no per-row query.
    """
    items = []
    for vat_item in VatComplianceRepository(ctx.db).get_overdue_unfiled(ctx.today):
        if (
            client_record_id is not None
            and vat_item.client_record_id != client_record_id
        ):
            continue
        due_date = _vat_due_date(vat_item)
        items.append(
            ctx.item(
                WorkQueueSourceType.VAT_FILING,
                vat_item.id,
                f'מע"מ לא הוגש: {vat_item.period}',
                due_date,
                vat_item.client_record_id,
                payload=vat_work_item_payload(vat_item, due_date),
            )
        )
    return items


def annual_report_items(
    ctx: WorkQueueContext, client_record_id: Optional[int]
) -> list[WorkQueueItem]:
    cutoff = ctx.today + timedelta(days=UPCOMING_WINDOW_DAYS)
    annual_report = annual_report_models.AnnualReport
    stmt = scope_to_active_clients_stmt(select(annual_report), annual_report).where(
        annual_report.deleted_at.is_(None),
        annual_report.filing_deadline.isnot(None),
        annual_report.filing_deadline <= cutoff,
        annual_report.status.notin_([s.value for s in _DONE_ANNUAL_STATUSES]),
    )
    if client_record_id is not None:
        stmt = stmt.where(annual_report.client_record_id == client_record_id)
    return [_annual_report_item(ctx, report) for report in ctx.db.scalars(stmt)]


def _annual_report_item(ctx: WorkQueueContext, report) -> WorkQueueItem:
    due_date = (
        report.filing_deadline.date()
        if hasattr(report.filing_deadline, "date")
        else report.filing_deadline
    )
    return ctx.item(
        WorkQueueSourceType.ANNUAL_REPORT,
        report.id,
        f"דוח שנתי {report.tax_year}",
        due_date,
        report.client_record_id,
        payload=annual_report_payload(report),
    )
