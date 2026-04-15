"""
VAT Invoice line-item ORM model.

Represents a single tax document (invoice, receipt, credit note, etc.)
attached to a VatWorkItem.

Design decisions:
- Amounts are always positive; credit notes are identified by document_type.
- invoice_date is Date (not DateTime) — VAT reporting is calendar-date based.
- No line-item breakdown — header-level totals sufficient for tax advisory work.
- counterparty_id_type enables validation routing (IL checksum vs. foreign).
"""

from sqlalchemy import (
    Boolean, Column, Date, ForeignKey,
    Index, Integer, Numeric, String, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.utils.enum_utils import pg_enum

from datetime import date

from app.database import Base
from app.vat_reports.models.vat_enums import (
    DocumentType,
    ExpenseCategory,
    InvoiceType,
    VatRateType,
    CounterpartyIdType
)



class VatInvoice(Base):
    __tablename__ = "vat_invoices"

    id                   = Column(Integer, primary_key=True, autoincrement=True)
    work_item_id         = Column(Integer, ForeignKey("vat_work_items.id", ondelete="CASCADE"),
                                  nullable=False, index=True)

    work_item = relationship("VatWorkItem", back_populates="invoices")
    created_by           = Column(Integer, ForeignKey("users.id"), nullable=False)
    # Optional tag: which BusinessActivity (branch/shop/service) contributed this invoice.
    # NULL = untagged (valid — e.g. client has only one activity or is a COMPANY_LTD).
    business_activity_id = Column(Integer, ForeignKey("businesses.id"),
                                  nullable=True, index=True)

    # Document classification
    invoice_type  = Column(pg_enum(InvoiceType), nullable=False)
    document_type = Column(pg_enum(DocumentType, name="vatdocumenttype"), nullable=True)
    # CREDIT_NOTE reversal is applied in service layer — amounts always positive here

    # Invoice identity
    invoice_number = Column(String, nullable=False)
    invoice_date   = Column(Date, nullable=False)  # Date only — no timezone issues

    # Counterparty
    counterparty_name    = Column(String, nullable=False)
    counterparty_id      = Column(String, nullable=True)   # מספר עוסק / ת"ז / דרכון
    counterparty_id_type = Column(pg_enum(CounterpartyIdType), nullable=True)
    # Validation routing: IL_BUSINESS/IL_PERSONAL → checksum; FOREIGN → free text

    # Amounts — always positive; credit notes identified via document_type
    net_amount = Column(Numeric(12, 2), nullable=False)
    vat_amount = Column(Numeric(12, 2), nullable=False)

    # VAT classification
    expense_category = Column(pg_enum(ExpenseCategory), nullable=True)
    rate_type        = Column(pg_enum(VatRateType), nullable=False,
                              default=VatRateType.STANDARD)
    deduction_rate   = Column(Numeric(5, 4), nullable=False, default=1.0000)
    # Auto-populated from CATEGORY_DEDUCTION_RATES on create/update

    # Exceptional invoice flag (> 25,000 ₪ net — requires special handling)
    is_exceptional = Column(Boolean, nullable=False, default=False)

    # Timestamp
    created_at = Column(Date, nullable=False, default=date.today)

    __table_args__ = (
        UniqueConstraint(
            "work_item_id", "invoice_type", "invoice_number",
            name="uq_vat_invoice_item_type_number",
        ),
        Index("ix_vat_invoices_work_item_type", "work_item_id", "invoice_type"),
        Index("ix_vat_invoices_date", "invoice_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<VatInvoice(id={self.id}, work_item_id={self.work_item_id}, "
            f"type={self.invoice_type}, number={self.invoice_number})>"
        )