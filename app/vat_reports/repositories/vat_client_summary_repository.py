"""Repository for client-level VAT summary queries."""

from decimal import Decimal

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.vat_reports.models.vat_enums import InvoiceType, VatWorkItemStatus
from app.vat_reports.models.vat_invoice import VatInvoice
from app.vat_reports.models.vat_work_item import VatWorkItem


class VatClientSummaryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_periods_for_client(self, client_id: int) -> list[tuple]:
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
            .filter(VatWorkItem.client_id == client_id)
            .order_by(VatWorkItem.period.desc())
            .all()
        )

    def get_annual_aggregates(self, client_id: int) -> list[tuple]:
        # מחזיר rows גולמיים — הסרוויס אחראי על המיפוי לschema
        year_expr = func.substr(VatWorkItem.period, 1, 4).label("year")
        filed_case = func.sum(
            case((VatWorkItem.status == VatWorkItemStatus.FILED, 1), else_=0)
        )
        # ... שאר השאילתה ללא שינוי, רק ללא .all() עם schema building