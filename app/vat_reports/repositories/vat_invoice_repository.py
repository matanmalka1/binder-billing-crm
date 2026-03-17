"""Repository for VatInvoice entities."""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.vat_reports.models.vat_enums import (
    DocumentType,
    ExpenseCategory,
    InvoiceType,
    VatRateType,
)
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
        rate_type: VatRateType = VatRateType.STANDARD,
        deduction_rate: float = 1.0,
        document_type: Optional[DocumentType] = None,
        is_exceptional: bool = False,
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
            rate_type=rate_type,
            deduction_rate=deduction_rate,
            document_type=document_type,
            is_exceptional=is_exceptional,
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

    def sum_vat_both_types(self, work_item_id: int) -> tuple[float, float]:
        """Return (output_vat, deductible_input_vat).

        - Output VAT: sum of vat_amount for INCOME invoices with STANDARD rate only
          (EXEMPT and ZERO_RATE contribute 0 to output VAT)
        - Input VAT: sum of vat_amount * deduction_rate for EXPENSE invoices
        """
        from decimal import Decimal

        from sqlalchemy import func

        from app.vat_reports.models.vat_enums import VatRateType

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

    def sum_income_net_by_client_year(self, client_id: int, year: int) -> float:
        """Sum net_amount of INCOME invoices for a client across a tax year.

        Used for OSEK PATUR ceiling enforcement.
        """
        from sqlalchemy import func

        from app.vat_reports.models.vat_work_item import VatWorkItem

        result = (
            self.db.query(func.sum(VatInvoice.net_amount))
            .join(VatWorkItem, VatInvoice.work_item_id == VatWorkItem.id)
            .filter(
                VatWorkItem.client_id == client_id,
                VatInvoice.invoice_type == InvoiceType.INCOME,
                VatWorkItem.period.like(f"{year}-%"),
            )
            .scalar()
        )
        return float(result or 0)

    def update(self, invoice_id: int, **fields) -> Optional[VatInvoice]:
        invoice = self.get_by_id(invoice_id)
        if not invoice:
            return None
        for key, value in fields.items():
            if value is not None:
                setattr(invoice, key, value)
        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def delete(self, invoice_id: int) -> bool:
        invoice = self.get_by_id(invoice_id)
        if not invoice:
            return False
        self.db.delete(invoice)
        self.db.commit()
        return True
