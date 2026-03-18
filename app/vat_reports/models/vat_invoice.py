"""VAT Invoice line-item ORM model."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from app.utils.enum_utils import pg_enum

from app.database import Base
from app.utils.time_utils import utcnow
from app.vat_reports.models.vat_enums import (
    DocumentType,
    ExpenseCategory,
    InvoiceType,
    VatRateType,
)


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
    invoice_type = Column(pg_enum(InvoiceType), nullable=False)
    invoice_number = Column(String, nullable=False)
    invoice_date = Column(DateTime, nullable=False)

    # Counterparty
    counterparty_name = Column(String, nullable=False)
    counterparty_id = Column(String, nullable=True)  # business ID / VAT number

    # Amounts (ILS, no negatives allowed)
    net_amount = Column(Numeric(12, 2), nullable=False)
    vat_amount = Column(Numeric(12, 2), nullable=False)

    # Expense-only classification
    expense_category = Column(pg_enum(ExpenseCategory), nullable=True)

    # VAT rate category (חייב / פטור / אפס)
    rate_type = Column(
        pg_enum(VatRateType), nullable=False, default=VatRateType.STANDARD
    )

    # Deduction rate for input VAT (0.0–1.0); auto-set from expense_category
    deduction_rate = Column(Numeric(5, 4), nullable=False, default=1.0000)

    # Document type (חשבונית מס / עסקה / קבלה / מרוכזת / עצמית)
    document_type = Column(pg_enum(DocumentType), nullable=True)

    # Exceptional invoice flag: net_amount > 25,000 ₪ requires special handling
    is_exceptional = Column(Boolean, nullable=False, default=False)

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
