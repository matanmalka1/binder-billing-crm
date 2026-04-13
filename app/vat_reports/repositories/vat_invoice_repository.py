"""Repository for VatInvoice CRUD operations.

Aggregation queries (sum_vat_both_types, sum_net_both_types,
sum_income_net_by_client_year) live in VatInvoiceAggregationRepository.
This class re-exposes them via composition for backward compatibility.
"""

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.vat_reports.models.vat_enums import (
    CounterpartyIdType,
    DocumentType,
    ExpenseCategory,
    InvoiceType,
    VatRateType,
)
from app.vat_reports.models.vat_invoice import VatInvoice
from app.vat_reports.repositories.vat_invoice_aggregation_repository import (
    VatInvoiceAggregationRepository,
)


class VatInvoiceRepository:
    def __init__(self, db: Session):
        self.db = db
        self._agg = VatInvoiceAggregationRepository(db)

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def create(
        self,
        work_item_id: int,
        created_by: int,
        invoice_type: InvoiceType,
        invoice_number: str,
        invoice_date: date,
        counterparty_name: str,
        net_amount: float,
        vat_amount: float,
        counterparty_id: Optional[str] = None,
        counterparty_id_type: Optional[CounterpartyIdType] = None,
        expense_category: Optional[ExpenseCategory] = None,
        rate_type: VatRateType = VatRateType.STANDARD,
        deduction_rate: float = 1.0,
        document_type: Optional[DocumentType] = None,
        is_exceptional: bool = False,
        business_activity_id: Optional[int] = None,
    ) -> VatInvoice:
        invoice = VatInvoice(
            work_item_id=work_item_id,
            created_by=created_by,
            invoice_type=invoice_type,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            counterparty_name=counterparty_name,
            counterparty_id=counterparty_id,
            counterparty_id_type=counterparty_id_type,
            net_amount=net_amount,
            vat_amount=vat_amount,
            expense_category=expense_category,
            rate_type=rate_type,
            deduction_rate=deduction_rate,
            document_type=document_type,
            is_exceptional=is_exceptional,
            business_activity_id=business_activity_id,
        )
        self.db.add(invoice)
        self.db.flush()
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

    def update(self, invoice_id: int, **fields) -> Optional[VatInvoice]:
        invoice = self.get_by_id(invoice_id)
        if not invoice:
            return None
        for key, value in fields.items():
            if value is not None:
                setattr(invoice, key, value)
        self.db.flush()
        return invoice

    def delete(self, invoice_id: int) -> bool:
        invoice = self.get_by_id(invoice_id)
        if not invoice:
            return False
        self.db.delete(invoice)
        self.db.flush()
        return True

    # ── Aggregation (delegated) ───────────────────────────────────────────────

    def sum_vat_both_types(self, work_item_id: int) -> tuple[float, float]:
        return self._agg.sum_vat_both_types(work_item_id)

    def sum_net_both_types(self, work_item_id: int) -> tuple[float, float]:
        return self._agg.sum_net_both_types(work_item_id)

    def sum_income_net_by_client_year(self, client_id: int, year: int) -> float:
        return self._agg.sum_income_net_by_client_year(client_id, year)

    def sum_expense_net_by_client_year_grouped(self, client_id: int, year: int) -> dict:
        return self._agg.sum_expense_net_by_client_year_grouped(client_id, year)

