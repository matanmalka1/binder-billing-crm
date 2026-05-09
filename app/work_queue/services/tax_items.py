from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select

from app.annual_reports import models as annual_report_models
from app.clients.repositories.active_client_scope import scope_to_active_clients_stmt
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.models.vat_work_item import VatWorkItem
from app.vat_reports.repositories.vat_compliance_repository import (
    VatComplianceRepository,
)
from app.work_queue.schemas.work_queue import WorkQueueItem, WorkQueueSourceType
from app.work_queue.services.common import UPCOMING_WINDOW_DAYS, WorkQueueContext
from app.work_queue.services.payloads import annual_report_payload, vat_work_item_payload

_DONE_ANNUAL_STATUSES = {
    annual_report_models.AnnualReportStatus.CLOSED,
    annual_report_models.AnnualReportStatus.CANCELED,
    annual_report_models.AnnualReportStatus.ACCEPTED,
}


def vat_filing_items(
    ctx: WorkQueueContext, client_record_id: Optional[int]
) -> list[WorkQueueItem]:
    items = []
    for row in VatComplianceRepository(ctx.db).get_overdue_unfiled(ctx.today):
        if client_record_id is not None and row.client_record_id != client_record_id:
            continue
        vat_item = ctx.db.scalars(
            select(VatWorkItem).where(
                VatWorkItem.client_record_id == row.client_record_id,
                VatWorkItem.period == row.period,
                VatWorkItem.status != VatWorkItemStatus.FILED,
                VatWorkItem.deleted_at.is_(None),
            )
        ).first()
        if not vat_item:
            continue
        due_date = date(int(row.period[:4]), int(row.period[5:7]), 19)
        items.append(
            ctx.item(
                WorkQueueSourceType.VAT_FILING,
                vat_item.id,
                f'מע"מ לא הוגש: {row.period}',
                due_date,
                row.client_record_id,
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
