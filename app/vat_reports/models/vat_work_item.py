"""
VAT Work Item ORM model.

Tracks the full lifecycle of a client's VAT reporting period:
  PENDING_MATERIALS → MATERIAL_RECEIVED → DATA_ENTRY_IN_PROGRESS
  → READY_FOR_REVIEW → FILED

Once FILED the period is immutable — no invoices may be added or edited.

Israeli context:
  VAT (מע"מ) is reported monthly or bi-monthly to the Israel Tax Authority.
  Output VAT (מע"מ עסקאות) minus Input VAT (מע"מ תשומות) = Net VAT payable.
  
  Fields 87/66 in the VAT return correspond to total_output_net/total_input_net.
  These are snapshotted at filing time and must not change post-submission.
"""

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey,
    Index, Integer, Numeric, String, Text, UniqueConstraint,
)
from app.utils.enum_utils import pg_enum

from app.database import Base
from app.utils.time_utils import utcnow
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.businesses.models.business_tax_profile import VatType
from app.annual_reports.models.annual_report_enums import SubmissionMethod

class VatWorkItem(Base):
    __tablename__ = "vat_work_items"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)
    created_by  = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Period identity
    period      = Column(String(7), nullable=False)   # "YYYY-MM"
    period_type = Column(pg_enum(VatType), nullable=False)  # snapshot: monthly/bimonthly

    # Status lifecycle
    status                 = Column(pg_enum(VatWorkItemStatus), nullable=False,
                                    default=VatWorkItemStatus.MATERIAL_RECEIVED)
    pending_materials_note = Column(Text, nullable=True)

    # Denormalized VAT totals (refreshed on every invoice mutation)
    total_output_vat = Column(Numeric(12, 2), nullable=False, default=0)
    total_input_vat  = Column(Numeric(12, 2), nullable=False, default=0)
    net_vat          = Column(Numeric(12, 2), nullable=False, default=0)

    # Denormalized net totals — fields 87/66 in VAT return
    # Snapshotted at filing; do not recalculate post-FILED
    total_output_net = Column(Numeric(12, 2), nullable=False, default=0)
    total_input_net  = Column(Numeric(12, 2), nullable=False, default=0)

    # Filing details (set when status → FILED)
    final_vat_amount       = Column(Numeric(12, 2), nullable=True)
    is_overridden          = Column(Boolean, nullable=False, default=False)
    override_justification = Column(Text, nullable=True)
    submission_method      = Column(pg_enum(SubmissionMethod), nullable=True)  # replaces filing_method
    filed_at               = Column(DateTime, nullable=True)
    filed_by               = Column(Integer, ForeignKey("users.id"), nullable=True)
    submission_reference   = Column(String(100), nullable=True)

    # Amendment tracking
    is_amendment   = Column(Boolean, nullable=False, default=False)
    amends_item_id = Column(Integer, ForeignKey("vat_work_items.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    # Soft delete
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint("business_id", "period", name="uq_vat_work_item_business_period"),
        Index("ix_vat_work_items_status", "status"),
        Index("ix_vat_work_items_period", "period"),
    )

    def __repr__(self) -> str:
        return (
            f"<VatWorkItem(id={self.id}, business_id={self.business_id}, "
            f"period={self.period}, status={self.status})>"
        )