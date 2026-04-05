"""Aggregation queries for VatInvoice entities."""

from decimal import Decimal
from typing import Optional

from sqlalchemy import func
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
        # Output VAT: only STANDARD-rate INCOME invoices
        output_row = (
            self.db.query(func.sum(VatInvoice.vat_amount))
            .filter(
                VatInvoice.work_item_id == work_item_id,
                VatInvoice.invoice_type == InvoiceType.INCOME,
                VatInvoice.rate_type == VatRateType.STANDARD,
            )
            .scalar()
        )
        output_vat = float(output_row or 0)

        # Input VAT: vat_amount * deduction_rate per invoice (computed in Python)
        expense_rows = (
            self.db.query(VatInvoice.vat_amount, VatInvoice.deduction_rate)
            .filter(
                VatInvoice.work_item_id == work_item_id,
                VatInvoice.invoice_type == InvoiceType.EXPENSE,
            )
            .all()
        )
        input_vat = float(
            sum(
                Decimal(str(row.vat_amount)) * Decimal(str(row.deduction_rate))
                for row in expense_rows
            )
        )
        return output_vat, input_vat

    def sum_net_both_types(self, work_item_id: int) -> tuple[float, float]:
        """Return (output_net, input_net) — sum of net_amount for INCOME and EXPENSE."""
        output_row = (
            self.db.query(func.sum(VatInvoice.net_amount))
            .filter(
                VatInvoice.work_item_id == work_item_id,
                VatInvoice.invoice_type == InvoiceType.INCOME,
            )
            .scalar()
        )
        input_row = (
            self.db.query(func.sum(VatInvoice.net_amount))
            .filter(
                VatInvoice.work_item_id == work_item_id,
                VatInvoice.invoice_type == InvoiceType.EXPENSE,
            )
            .scalar()
        )
        return float(output_row or 0), float(input_row or 0)

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
