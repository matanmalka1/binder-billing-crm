"""Grouped/due-date-level queries for VatWorkItem."""

from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.repositories.active_client_scope import scope_to_active_clients_stmt
from app.common.enums import VatType
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.models.vat_work_item import VatWorkItem
from app.vat_reports.repositories.vat_work_item_filters import (
    apply_vat_work_item_filters,
)


def _base_stmt():
    return scope_to_active_clients_stmt(select(VatWorkItem), VatWorkItem).where(
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
    stmt = apply_vat_work_item_filters(
        _base_stmt(),
        period_type=period_type,
        client_record_ids=client_record_ids,
    )
    if year is not None:
        stmt = stmt.where(VatWorkItem.period.startswith(f"{year}-"))
    if status is not None:
        stmt = stmt.where(VatWorkItem.status == status)

    rows = db.scalars(stmt).all()

    groups: dict[str, dict] = {}
    for row in rows:
        if row.due_date_effective is None:
            continue

        deadline = row.due_date_effective
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
            g["periods"].sort(
                key=lambda p: (
                    0 if p["period_type"] == VatType.BIMONTHLY else 1,
                    p["period"],
                )
            )
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
    stmt = apply_vat_work_item_filters(
        _base_stmt(),
        client_record_ids=client_record_ids,
    )
    if status is not None:
        stmt = stmt.where(VatWorkItem.status == status)

    stmt = stmt.where(VatWorkItem.due_date_effective == due_date)
    matching = db.scalars(stmt).all()
    total = len(matching)
    start = (page - 1) * page_size
    items = sorted(matching, key=lambda item: item.client_record_id)[
        start : start + page_size
    ]
    return items, total
