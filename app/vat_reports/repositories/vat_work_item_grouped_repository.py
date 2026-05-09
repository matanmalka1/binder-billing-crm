"""Grouped/due-date-level queries for VatWorkItem."""

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.clients.repositories.active_client_scope import scope_to_active_clients
from app.common.enums import VatType
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.models.vat_work_item import VatWorkItem
from app.vat_reports.repositories.vat_work_item_filters import (
    apply_vat_work_item_filters,
)
from app.vat_reports.services.vat_report_queries import compute_deadline_fields


def _base_query(db: Session):
    return scope_to_active_clients(db.query(VatWorkItem), VatWorkItem).filter(
        VatWorkItem.deleted_at.is_(None)
    )


def list_due_date_groups(
    db: Session,
    *,
    period_type: Optional[VatType] = None,
    client_record_ids: Optional[list[int]] = None,
    status: Optional[VatWorkItemStatus] = None,
    year: Optional[int] = None,
) -> list[dict]:
    """One summary dict per operational due date."""
    q = apply_vat_work_item_filters(
        _base_query(db),
        period_type=period_type,
        client_record_ids=client_record_ids,
    )
    if year is not None:
        q = q.filter(VatWorkItem.period.startswith(f"{year}-"))
    if status is not None:
        q = q.filter(VatWorkItem.status == status)

    rows = q.with_entities(
        VatWorkItem.period,
        VatWorkItem.period_type,
        VatWorkItem.status,
        VatWorkItem.due_date_effective,
    ).all()

    groups: dict[str, dict] = {}
    for row in rows:
        # Prefer persisted effective date (registry-shifted statutory).
        # Fall back to legacy period-based computation only for pre-linking rows.
        if row.due_date_effective is not None:
            deadline = row.due_date_effective
        else:
            deadline = compute_deadline_fields(row)["submission_deadline"]
        if deadline is None:
            continue
        due_date = deadline.isoformat()
        if due_date not in groups:
            groups[due_date] = {
                "group_key": due_date,
                "due_date": deadline,
                "period": row.period,
                "period_type": row.period_type,
                "periods": [],
                "total_count": 0,
                "filed_count": 0,
                "pending_count": 0,
            }
        g = groups[due_date]
        period_summary = {
            "period": row.period,
            "period_type": row.period_type,
        }
        if period_summary not in g["periods"]:
            g["periods"].append(period_summary)
        g["total_count"] += 1
        if row.status == VatWorkItemStatus.FILED:
            g["filed_count"] += 1
        if row.status == VatWorkItemStatus.PENDING_MATERIALS:
            g["pending_count"] += 1

    return sorted(groups.values(), key=lambda g: g["due_date"])


def list_by_due_date_paginated(
    db: Session,
    due_date: date,
    *,
    page: int = 1,
    page_size: int = 50,
    client_record_ids: Optional[list[int]] = None,
    status: Optional[VatWorkItemStatus] = None,
) -> tuple[list[VatWorkItem], int]:
    q = apply_vat_work_item_filters(
        _base_query(db),
        client_record_ids=client_record_ids,
    )
    if status is not None:
        q = q.filter(VatWorkItem.status == status)
    # Group membership is tested against the statutory/effective calendar date, not the online
    # submission deadline. Intentionally does NOT use get_vat_deadline_fields: that helper may
    # add the online extension (+4 days) and would cause online-filer items to miss their group.
    # Linked rows (due_date_effective set): match directly against the persisted statutory date.
    # Legacy unlinked rows (due_date_effective None): recompute from period+15 as fallback.
    matching = [
        item
        for item in q.all()
        if (
            item.due_date_effective
            if item.due_date_effective is not None
            else compute_deadline_fields(item)["submission_deadline"]
        )
        == due_date
    ]
    total = len(matching)
    start = (page - 1) * page_size
    items = sorted(matching, key=lambda item: item.client_record_id)[
        start : start + page_size
    ]
    return items, total
