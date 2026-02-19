"""VAT Invoice line-item ORM model."""

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)

from app.database import Base
from app.utils.time import utcnow
from app.vat_reports.models.vat_enums import ExpenseCategory, InvoiceType


class VatInvoice(Base):
    """
    A single income or expense invoice line attached to a VatWorkItem.

    Invoice numbers must be unique per client per period per type to prevent
    duplicate entry.
    """

    __tablename__ = "vat_invoices"

    id = Column(Integer, primary_key=True, autoincrement=True)

    work_item_id = Column(
        Integer, ForeignKey("vat_work_items.id"), nullable=False, index=True
    )
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Invoice identity
    invoice_type = Column(Enum(InvoiceType), nullable=False)
    invoice_number = Column(String, nullable=False)
    invoice_date = Column(DateTime, nullable=False)

    # Counterparty
    counterparty_name = Column(String, nullable=False)
    counterparty_id = Column(String, nullable=True)  # business ID / VAT number

    # Amounts (ILS, no negatives allowed)
    net_amount = Column(Numeric(12, 2), nullable=False)
    vat_amount = Column(Numeric(12, 2), nullable=False)

    # Expense-only classification
    expense_category = Column(Enum(ExpenseCategory), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utcnow)

    __table_args__ = (
        UniqueConstraint(
            "work_item_id",
            "invoice_type",
            "invoice_number",
            name="uq_vat_invoice_item_type_number",
        ),
        Index("ix_vat_invoices_work_item_type", "work_item_id", "invoice_type"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<VatInvoice(id={self.id}, work_item_id={self.work_item_id}, "
            f"type={self.invoice_type}, number={self.invoice_number})>"
        )
