from typing import Optional

from sqlalchemy import func as sa_func

from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.models.vat_work_item import VatWorkItem


def sum_net_vat_by_client_record_year(db, client_record_id: int, tax_year: int) -> Optional[float]:
    row = (
        db.query(sa_func.sum(VatWorkItem.net_vat).label("total_vat"))
        .filter(
            VatWorkItem.client_record_id == client_record_id,
            sa_func.substr(VatWorkItem.period, 1, 4) == str(tax_year),
            VatWorkItem.deleted_at.is_(None),
        )
        .one_or_none()
    )
    return float(row[0]) if row and row[0] is not None else None


def list_not_filed_for_period(db, period: str, limit: int = 3) -> list[VatWorkItem]:
    return (
        db.query(VatWorkItem)
        .filter(
            VatWorkItem.period == period,
            VatWorkItem.status != VatWorkItemStatus.FILED,
            VatWorkItem.deleted_at.is_(None),
        )
        .order_by(VatWorkItem.created_at.asc())
        .limit(limit)
        .all()
    )


def list_by_business_activity(db, business_activity_id: int, limit: int = 200) -> list[VatWorkItem]:
    from app.vat_reports.models.vat_invoice import VatInvoice
    return (
        db.query(VatWorkItem)
        .join(VatInvoice, VatInvoice.work_item_id == VatWorkItem.id)
        .filter(VatInvoice.business_activity_id == business_activity_id, VatWorkItem.deleted_at.is_(None))
        .distinct()
        .order_by(VatWorkItem.period.desc())
        .limit(limit)
        .all()
    )
