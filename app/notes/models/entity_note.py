"""
EntityNote — centralized notes attached to any domain entity.

Design decisions:
- entity_type is String so it can represent any domain without migrations.
- entity_id identifies the target row in that domain.
- note stores the note body.
- records are mutable and soft-deletable, matching the rest of the codebase.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text

from app.database import Base
from app.utils.time_utils import utcnow


class EntityNote(Base):
    __tablename__ = "entity_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String, nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)
    note = Column(Text, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=utcnow)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        Index("idx_entity_notes_type_id", "entity_type", "entity_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<EntityNote(id={self.id}, entity_type={self.entity_type}, "
            f"entity_id={self.entity_id})>"
        )
