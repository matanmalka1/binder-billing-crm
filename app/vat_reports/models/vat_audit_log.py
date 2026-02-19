"""VAT Audit Log — append-only audit trail for every work item action."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base
from app.utils.time import utcnow


class VatAuditLog(Base):
    """
    Immutable record of every status change, invoice addition, and override
    performed on a VatWorkItem.  Never updated or deleted.
    """

    __tablename__ = "vat_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    work_item_id = Column(
        Integer, ForeignKey("vat_work_items.id"), nullable=False, index=True
    )
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    action = Column(String, nullable=False)       # e.g. "status_changed", "invoice_added", "override"
    old_value = Column(Text, nullable=True)       # JSON-serialised previous state fragment
    new_value = Column(Text, nullable=True)       # JSON-serialised new state fragment
    note = Column(Text, nullable=True)

    performed_at = Column(DateTime, nullable=False, default=utcnow)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<VatAuditLog(id={self.id}, work_item_id={self.work_item_id}, "
            f"action={self.action})>"
        )
