"""Aggregation queries for VatInvoice entities."""

from decimal import Decimal
from typing import Optional

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.vat_reports.models.vat_enums import InvoiceType, VatRateType
from app.vat_reports.models.vat_invoice import VatInvoice
from app.vat_reports.models.vat_work_item import VatWorkItem


class VatInvoiceAggregationRepository:
    def __init__(self, db: Session):
        self.db = db

    def sum_vat_both_types(self, work_item_id: int) -> tuple[float, float]:
        """Return (output_vat, deductible_input_vat).

        - Output VAT: sum of vat_amount for INCOME invoices with STANDARD rate only
          (EXEMPT and ZERO_RATE contribute 0 to output VAT)
        - Input VAT: sum of vat_amount * deduction_rate for EXPENSE invoices
        """
        rows = (
            self.db.query(
                VatInvoice.invoice_type,
                func.sum(
                    case(
                        (
                            VatInvoice.invoice_type == InvoiceType.INCOME,
                            case(
                                (
                                    VatInvoice.rate_type == VatRateType.STANDARD,
                                    VatInvoice.vat_amount,
                                ),
                                else_=0,
                            ),
                        ),
                        (
                            VatInvoice.invoice_type == InvoiceType.EXPENSE,
                            VatInvoice.vat_amount * VatInvoice.deduction_rate,
                        ),
                        else_=0,
                    )
                ).label("total"),
            )
            .filter(
                VatInvoice.work_item_id == work_item_id,
                VatInvoice.invoice_type.in_((InvoiceType.INCOME, InvoiceType.EXPENSE)),
            )
            .group_by(VatInvoice.invoice_type)
            .all()
        )
        grouped = {
            row.invoice_type: Decimal(str(row.total or 0))
            for row in rows
        }
        output_vat = float(grouped.get(InvoiceType.INCOME, Decimal("0")))
        input_vat = float(grouped.get(InvoiceType.EXPENSE, Decimal("0")))
        return output_vat, input_vat

    def sum_net_both_types(self, work_item_id: int) -> tuple[float, float]:
        """Return (output_net, input_net) — sum of net_amount for INCOME and EXPENSE."""
        rows = (
            self.db.query(
                VatInvoice.invoice_type,
                func.sum(VatInvoice.net_amount).label("total"),
            )
            .filter(
                VatInvoice.work_item_id == work_item_id,
                VatInvoice.invoice_type.in_((InvoiceType.INCOME, InvoiceType.EXPENSE)),
            )
            .group_by(VatInvoice.invoice_type)
            .all()
        )
        grouped = {
            row.invoice_type: float(row.total or 0)
            for row in rows
        }
        return (
            grouped.get(InvoiceType.INCOME, 0.0),
            grouped.get(InvoiceType.EXPENSE, 0.0),
        )

    def sum_income_net_by_business_year(self, business_id: int, year: int) -> float:
        """Sum net_amount of INCOME invoices for a business across a tax year.

        Used for OSEK PATUR ceiling enforcement.
        """
        result = (
            self.db.query(func.sum(VatInvoice.net_amount))
            .join(VatWorkItem, VatInvoice.work_item_id == VatWorkItem.id)
            .filter(
                VatWorkItem.business_id == business_id,
                VatInvoice.invoice_type == InvoiceType.INCOME,
                VatWorkItem.period.like(f"{year}-%"),
                VatWorkItem.deleted_at.is_(None),
            )
            .scalar()
        )
        return float(result or 0)

    def sum_expense_net_by_business_year_grouped(
        self, business_id: int, year: int
    ) -> dict[str, float]:
        """Return {expense_category_value: total_net_amount} for EXPENSE invoices.

        Aggregates across all work items for this business in the given tax year.
        Used by annual reports auto-population to map VAT expense categories.
        """
        rows = (
            self.db.query(
                VatInvoice.expense_category,
                func.sum(VatInvoice.net_amount).label("total"),
            )
            .join(VatWorkItem, VatInvoice.work_item_id == VatWorkItem.id)
            .filter(
                VatWorkItem.business_id == business_id,
                VatInvoice.invoice_type == InvoiceType.EXPENSE,
                VatWorkItem.period.like(f"{year}-%"),
                VatWorkItem.deleted_at.is_(None),
            )
            .group_by(VatInvoice.expense_category)
            .all()
        )
        return {
            (row.expense_category.value if row.expense_category else "other"): float(row.total or 0)
            for row in rows
        }
