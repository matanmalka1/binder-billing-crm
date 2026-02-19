"""
VAT Work Item ORM model.

Tracks the full lifecycle of a client's monthly VAT reporting:
  PENDING_MATERIALS → MATERIAL_RECEIVED → DATA_ENTRY_IN_PROGRESS
  → READY_FOR_REVIEW → FILED

Once FILED the period is immutable — no invoices may be added or edited.

Israeli context:
  VAT (מע"מ) is reported monthly or bi-monthly to the Israel Tax Authority.
  Output VAT (מע"מ עסקאות) minus Input VAT (מע"מ תשומות) = Net VAT payable.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)

from app.database import Base
from app.utils.time import utcnow
from app.vat_reports.models.vat_enums import FilingMethod, VatWorkItemStatus


class VatWorkItem(Base):
    """
    One VAT reporting period for a single client.

    Uniqueness: one work item per (client_id, period) — e.g. ("2026-01").
    """

    __tablename__ = "vat_work_items"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Relationships
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Period identity — stored as "YYYY-MM" string for simplicity
    period = Column(String(7), nullable=False)  # e.g. "2026-01"

    # Status lifecycle
    status = Column(
        Enum(VatWorkItemStatus),
        nullable=False,
        default=VatWorkItemStatus.MATERIAL_RECEIVED,
    )

    # Missing-materials note (only relevant when status = PENDING_MATERIALS)
    pending_materials_note = Column(Text, nullable=True)

    # Calculated totals (kept denormalised for fast reads; refreshed on every invoice upsert)
    total_output_vat = Column(Numeric(12, 2), nullable=False, default=0)
    total_input_vat = Column(Numeric(12, 2), nullable=False, default=0)
    net_vat = Column(Numeric(12, 2), nullable=False, default=0)  # output – input

    # Filing details (set when status → FILED)
    final_vat_amount = Column(Numeric(12, 2), nullable=True)
    is_overridden = Column(Boolean, nullable=False, default=False)
    override_justification = Column(Text, nullable=True)
    filing_method = Column(Enum(FilingMethod), nullable=True)
    filed_at = Column(DateTime, nullable=True)
    filed_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        UniqueConstraint("client_id", "period", name="uq_vat_work_item_client_period"),
        Index("ix_vat_work_items_status", "status"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<VatWorkItem(id={self.id}, client_id={self.client_id}, "
            f"period={self.period}, status={self.status})>"
        )
