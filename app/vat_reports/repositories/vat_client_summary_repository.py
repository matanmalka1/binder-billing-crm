"""Repository for client-level VAT summary queries."""

from decimal import Decimal
from typing import Optional

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.vat_reports.models.vat_enums import InvoiceType, VatWorkItemStatus
from app.vat_reports.models.vat_invoice import VatInvoice
from app.vat_reports.models.vat_work_item import VatWorkItem
from app.vat_reports.schemas.vat_client_summary_schema import (
    VatAnnualSummary,
    VatPeriodRow,
)


class VatClientSummaryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_periods_for_client(self, client_id: int) -> list[VatPeriodRow]:
        # Subquery: sum net_amount per work_item_id per invoice_type
        net_sq = (
            self.db.query(
                VatInvoice.work_item_id,
                func.sum(
                    case(
                        (VatInvoice.invoice_type == InvoiceType.INCOME, VatInvoice.net_amount),
                        else_=0,
                    )
                ).label("output_net"),
                func.sum(
                    case(
                        (VatInvoice.invoice_type == InvoiceType.EXPENSE, VatInvoice.net_amount),
                        else_=0,
                    )
                ).label("input_net"),
            )
            .group_by(VatInvoice.work_item_id)
            .subquery()
        )

        rows = (
            self.db.query(VatWorkItem, net_sq.c.output_net, net_sq.c.input_net)
            .outerjoin(net_sq, VatWorkItem.id == net_sq.c.work_item_id)
            .filter(VatWorkItem.client_id == client_id)
            .order_by(VatWorkItem.period.desc())
            .all()
        )
        return [
            VatPeriodRow(
                work_item_id=r.id,
                period=r.period,
                status=r.status,
                total_output_vat=r.total_output_vat,
                total_input_vat=r.total_input_vat,
                net_vat=r.net_vat,
                total_output_net=Decimal(str(output_net or 0)),
                total_input_net=Decimal(str(input_net or 0)),
                final_vat_amount=r.final_vat_amount,
                filed_at=r.filed_at,
            )
            for r, output_net, input_net in rows
        ]

    def get_annual_aggregates(self, client_id: int) -> list[VatAnnualSummary]:
        year_expr = func.substr(VatWorkItem.period, 1, 4).label("year")
        filed_case = func.sum(
            case(
                (VatWorkItem.status == VatWorkItemStatus.FILED, 1),
                else_=0,
            )
        ).label("filed_count")

        rows = (
            self.db.query(
                year_expr,
                func.sum(VatWorkItem.total_output_vat).label("total_output_vat"),
                func.sum(VatWorkItem.total_input_vat).label("total_input_vat"),
                func.sum(VatWorkItem.net_vat).label("net_vat"),
                func.count(VatWorkItem.id).label("periods_count"),
                filed_case,
            )
            .filter(VatWorkItem.client_id == client_id)
            .group_by(year_expr)
            .order_by(year_expr.desc())
            .all()
        )
        return [
            VatAnnualSummary(
                year=int(r.year),
                total_output_vat=Decimal(str(r.total_output_vat or 0)),
                total_input_vat=Decimal(str(r.total_input_vat or 0)),
                net_vat=Decimal(str(r.net_vat or 0)),
                periods_count=r.periods_count,
                filed_count=r.filed_count,
            )
            for r in rows
        ]

    def get_annual_output_vat(self, client_id: int, year: int) -> Optional[Decimal]:
        """Sum total_output_vat for all VatWorkItems in a given year for a client."""
        prefix = f"{year}-%"
        result = (
            self.db.query(func.sum(VatWorkItem.total_output_vat))
            .filter(
                VatWorkItem.client_id == client_id,
                VatWorkItem.period.like(prefix),
            )
            .scalar()
        )
        if result is None:
            return None
        return Decimal(str(result))
