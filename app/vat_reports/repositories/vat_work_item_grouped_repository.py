"""Grouped/period-level queries for VatWorkItem."""

from typing import Optional

from sqlalchemy.orm import Session

from app.clients.repositories.active_client_scope import scope_to_active_clients
from app.common.enums import VatType
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.models.vat_work_item import VatWorkItem
from app.vat_reports.repositories.vat_work_item_filters import apply_vat_work_item_filters


def _base_query(db: Session):
    return scope_to_active_clients(
        db.query(VatWorkItem), VatWorkItem
    ).filter(VatWorkItem.deleted_at.is_(None))


def list_periods_grouped(
    db: Session,
    *,
    period_type: Optional[VatType] = None,
    client_record_ids: Optional[list[int]] = None,
    status: Optional[VatWorkItemStatus] = None,
    year: Optional[int] = None,
) -> list[dict]:
    """One summary dict per period, sorted desc."""
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
    ).all()

    groups: dict[str, dict] = {}
    for row in rows:
        if row.period not in groups:
            groups[row.period] = {
                "period": row.period,
                "period_type": row.period_type,
                "total_count": 0,
                "filed_count": 0,
                "pending_count": 0,
            }
        g = groups[row.period]
        g["total_count"] += 1
        if row.status == VatWorkItemStatus.FILED:
            g["filed_count"] += 1
        if row.status == VatWorkItemStatus.PENDING_MATERIALS:
            g["pending_count"] += 1

    return sorted(groups.values(), key=lambda g: g["period"], reverse=True)


def list_by_period_paginated(
    db: Session,
    period: str,
    *,
    page: int = 1,
    page_size: int = 50,
    client_record_ids: Optional[list[int]] = None,
    status: Optional[VatWorkItemStatus] = None,
) -> tuple[list[VatWorkItem], int]:
    q = apply_vat_work_item_filters(
        _base_query(db),
        period=period,
        client_record_ids=client_record_ids,
    )
    if status is not None:
        q = q.filter(VatWorkItem.status == status)
    total = q.count()
    items = (
        q.order_by(VatWorkItem.client_record_id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total
