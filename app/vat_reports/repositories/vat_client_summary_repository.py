"""Repository for business-level VAT summary queries."""

from sqlalchemy import case, func, Integer, cast
from sqlalchemy.orm import Session

from app.vat_reports.models.vat_enums import InvoiceType, VatWorkItemStatus
from app.vat_reports.models.vat_invoice import VatInvoice
from app.vat_reports.models.vat_work_item import VatWorkItem


class VatClientSummaryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_annual_output_vat(self, business_id: int, year: int):
        return (
            self.db.query(func.sum(VatWorkItem.total_output_vat))
            .filter(
                VatWorkItem.business_id == business_id,
                VatWorkItem.period.like(f"{year}-%"),
                VatWorkItem.deleted_at.is_(None),
            )
            .scalar()
        )

    def get_periods_for_business(self, business_id: int) -> list[tuple]:
        net_sq = (
            self.db.query(
                VatInvoice.work_item_id,
                func.sum(
                    case((VatInvoice.invoice_type == InvoiceType.INCOME, VatInvoice.net_amount), else_=0)
                ).label("output_net"),
                func.sum(
                    case((VatInvoice.invoice_type == InvoiceType.EXPENSE, VatInvoice.net_amount), else_=0)
                ).label("input_net"),
            )
            .group_by(VatInvoice.work_item_id)
            .subquery()
        )

        return (
            self.db.query(VatWorkItem, net_sq.c.output_net, net_sq.c.input_net)
            .outerjoin(net_sq, VatWorkItem.id == net_sq.c.work_item_id)
            .filter(
                VatWorkItem.business_id == business_id,
                VatWorkItem.deleted_at.is_(None),
            )
            .order_by(VatWorkItem.period.desc())
            .all()
        )

    def get_annual_aggregates(self, business_id: int) -> list[dict[str, object]]:
        year_expr = cast(func.substr(VatWorkItem.period, 1, 4), Integer).label("year")
        rows = (
            self.db.query(
                year_expr,
                func.sum(VatWorkItem.total_output_vat).label("total_output_vat"),
                func.sum(VatWorkItem.total_input_vat).label("total_input_vat"),
                func.sum(VatWorkItem.net_vat).label("net_vat"),
                func.count(VatWorkItem.id).label("periods_count"),
                func.sum(
                    case((VatWorkItem.status == VatWorkItemStatus.FILED, 1), else_=0)
                ).label("filed_count"),
            )
            .filter(
                VatWorkItem.business_id == business_id,
                VatWorkItem.deleted_at.is_(None),
            )
            .group_by(year_expr)
            .order_by(year_expr.desc())
            .all()
        )

        return [
            {
                "year": row.year,
                "total_output_vat": row.total_output_vat,
                "total_input_vat": row.total_input_vat,
                "net_vat": row.net_vat,
                "periods_count": row.periods_count,
                "filed_count": row.filed_count,
            }
            for row in rows
        ]