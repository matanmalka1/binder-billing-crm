from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, Integer, String, Text

from app.database import Base
from app.utils.time import utcnow


class CorrespondenceType(str, PyEnum):
    CALL = "call"
    LETTER = "letter"
    EMAIL = "email"
    MEETING = "meeting"


class Correspondence(Base):
    __tablename__ = "correspondence_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    contact_id = Column(
        Integer, ForeignKey("authority_contacts.id"), nullable=True, index=True
    )
    correspondence_type = Column(Enum(CorrespondenceType), nullable=False)
    subject = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    occurred_at = Column(DateTime, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        Index("idx_correspondence_client", "client_id"),
        Index("idx_correspondence_occurred", "occurred_at"),
    )

    def __repr__(self):
        return (
            f"<Correspondence(id={self.id}, client_id={self.client_id}, "
            f"type='{self.correspondence_type}', subject='{self.subject}')>"
        )
