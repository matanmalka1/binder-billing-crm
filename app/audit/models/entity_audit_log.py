"""
EntityAuditLog — generic, append-only audit trail for domain mutations.

Design decisions:
- entity_type is String (not enum) — expands freely without migrations.
  Use ENTITY_* constants from app/audit/constants.py.
- action is String — use ACTION_* constants, never raw strings in service code.
- old_value / new_value are JSON snapshots of the changed fields only (not full rows).
- NO soft delete — audit logs are immutable by design.
  Corrections are made by appending new entries, never deleting old ones.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text

from app.database import Base
from app.utils.time_utils import utcnow


class EntityAuditLog(Base):
    __tablename__ = "entity_audit_logs"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    entity_type  = Column(String, nullable=False, index=True)
    entity_id    = Column(Integer, nullable=False, index=True)
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Use ACTION_* constants from app/audit/constants.py
    action    = Column(String, nullable=False)
    old_value = Column(Text, nullable=True)   # JSON snapshot before mutation
    new_value = Column(Text, nullable=True)   # JSON snapshot after mutation
    note      = Column(Text, nullable=True)

    performed_at = Column(DateTime, nullable=False, default=utcnow)

    __table_args__ = (
        Index("idx_entity_audit_type_id", "entity_type", "entity_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<EntityAuditLog(id={self.id}, entity_type={self.entity_type}, "
            f"entity_id={self.entity_id}, action={self.action})>"
        )
