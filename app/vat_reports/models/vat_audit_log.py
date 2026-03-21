"""
VAT Audit Log — append-only audit trail for every work item action.

Design decisions:
- action is String (not enum) — expands freely without migrations.
  Use ACTION_* constants from vat_reports/services/constants.py.
- invoice_id is a direct FK for efficient per-invoice history queries.
  SET NULL on invoice delete — log entry is preserved even if invoice is gone.
- NO soft delete — audit logs are immutable by design.
  Corrections are made by appending new entries, never deleting old ones.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base
from app.utils.time_utils import utcnow


class VatAuditLog(Base):
    __tablename__ = "vat_audit_logs"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    work_item_id = Column(Integer, ForeignKey("vat_work_items.id"),
                          nullable=False, index=True)
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Use ACTION_* constants from constants.py — never raw strings in service code
    action    = Column(String, nullable=False)
    old_value = Column(Text, nullable=True)   # JSON snapshot
    new_value = Column(Text, nullable=True)   # JSON snapshot
    note      = Column(Text, nullable=True)

    # Direct FK for efficient "show history of invoice X" queries
    invoice_id = Column(
        Integer,
        ForeignKey("vat_invoices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    performed_at = Column(DateTime, nullable=False, default=utcnow)

    def __repr__(self) -> str:
        return (
            f"<VatAuditLog(id={self.id}, work_item_id={self.work_item_id}, "
            f"action={self.action})>"
        )