from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from app.utils.enum_utils import pg_enum

from app.database import Base
from app.utils.time_utils import utcnow

# ─── Correspondence ───────────────────────────────────────────────────────────
 
class CorrespondenceType(str, PyEnum):
    CALL = "call"
    LETTER = "letter"
    EMAIL = "email"
    MEETING = "meeting"
 
 
class Correspondence(Base):
    __tablename__ = "correspondence_entries"
 
    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("authority_contacts.id"), nullable=True, index=True)
    correspondence_type = Column(pg_enum(CorrespondenceType), nullable=False)
    subject = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    occurred_at = Column(DateTime, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
 
    __table_args__ = (
        Index("idx_correspondence_business", "business_id"),
        Index("idx_correspondence_occurred", "occurred_at"),
    )
 
    def __repr__(self):
        return f"<Correspondence(id={self.id}, business_id={self.business_id}, type='{self.correspondence_type}')>"
 
