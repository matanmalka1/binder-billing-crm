"""Repository for VatInvoice entities."""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.vat_reports.models.vat_enums import ExpenseCategory, InvoiceType
from app.vat_reports.models.vat_invoice import VatInvoice


class VatInvoiceRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        work_item_id: int,
        created_by: int,
        invoice_type: InvoiceType,
        invoice_number: str,
        invoice_date: datetime,
        counterparty_name: str,
        net_amount: float,
        vat_amount: float,
        counterparty_id: Optional[str] = None,
        expense_category: Optional[ExpenseCategory] = None,
    ) -> VatInvoice:
        invoice = VatInvoice(
            work_item_id=work_item_id,
            created_by=created_by,
            invoice_type=invoice_type,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            counterparty_name=counterparty_name,
            counterparty_id=counterparty_id,
            net_amount=net_amount,
            vat_amount=vat_amount,
            expense_category=expense_category,
        )
        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def get_by_id(self, invoice_id: int) -> Optional[VatInvoice]:
        return self.db.query(VatInvoice).filter(VatInvoice.id == invoice_id).first()

    def get_by_number(
        self, work_item_id: int, invoice_type: InvoiceType, invoice_number: str
    ) -> Optional[VatInvoice]:
        return (
            self.db.query(VatInvoice)
            .filter(
                VatInvoice.work_item_id == work_item_id,
                VatInvoice.invoice_type == invoice_type,
                VatInvoice.invoice_number == invoice_number,
            )
            .first()
        )

    def list_by_work_item(
        self,
        work_item_id: int,
        invoice_type: Optional[InvoiceType] = None,
    ) -> list[VatInvoice]:
        q = self.db.query(VatInvoice).filter(VatInvoice.work_item_id == work_item_id)
        if invoice_type:
            q = q.filter(VatInvoice.invoice_type == invoice_type)
        return q.order_by(VatInvoice.invoice_date.asc()).all()

    def sum_vat_by_type(self, work_item_id: int, invoice_type: InvoiceType) -> float:
        from sqlalchemy import func

        result = (
            self.db.query(func.coalesce(func.sum(VatInvoice.vat_amount), 0))
            .filter(
                VatInvoice.work_item_id == work_item_id,
                VatInvoice.invoice_type == invoice_type,
            )
            .scalar()
        )
        return float(result)

    def sum_vat_both_types(self, work_item_id: int) -> tuple[float, float]:
        """Return (output_vat, input_vat) in a single grouped query."""
        from sqlalchemy import func

        rows = (
            self.db.query(VatInvoice.invoice_type, func.sum(VatInvoice.vat_amount))
            .filter(VatInvoice.work_item_id == work_item_id)
            .group_by(VatInvoice.invoice_type)
            .all()
        )
        totals = {row[0]: float(row[1]) for row in rows}
        return totals.get(InvoiceType.INCOME, 0.0), totals.get(InvoiceType.EXPENSE, 0.0)

    def delete(self, invoice_id: int) -> bool:
        invoice = self.get_by_id(invoice_id)
        if not invoice:
            return False
        self.db.delete(invoice)
        self.db.commit()
        return True
