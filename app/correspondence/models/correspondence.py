"""
Correspondence — log of all interactions with a business or authority contact.

Israeli context:
  Tax advisors maintain detailed correspondence logs for audit purposes and
  ITA disputes. Entries cover calls with the tax authority, letters sent,
  meetings with clients, and email exchanges.

Design decisions:
- occurred_at is DateTime (not Date) — meetings and calls have a specific time.
- contact_id links to AuthorityContact (רשות המסים, ביטוח לאומי, etc.) —
  nullable because not all correspondence involves an authority contact.
- No updated_at — correspondence entries are immutable once created;
  corrections are soft-deleted and re-entered.
- Soft delete included — business entity.
"""

from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from app.utils.enum_utils import pg_enum

from app.database import Base
from app.utils.time_utils import utcnow


class CorrespondenceType(str, PyEnum):
    CALL    = "call"     # שיחת טלפון
    LETTER  = "letter"   # מכתב / דואר רשום
    EMAIL   = "email"    # דואר אלקטרוני
    MEETING = "meeting"  # פגישה פיזית או זום


class Correspondence(Base):
    __tablename__ = "correspondence_entries"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)
    contact_id  = Column(Integer, ForeignKey("authority_contacts.id"), nullable=True, index=True)

    # ── Content ───────────────────────────────────────────────────────────────
    correspondence_type = Column(pg_enum(CorrespondenceType), nullable=False)
    subject             = Column(String, nullable=False)
    notes               = Column(Text, nullable=True)
    occurred_at         = Column(DateTime, nullable=False)  # מתי התרחש האירוע בפועל

    # ── Metadata ──────────────────────────────────────────────────────────────
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    # ── Soft delete ───────────────────────────────────────────────────────────
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        Index("idx_correspondence_business",          "business_id"),
        Index("idx_correspondence_occurred",          "occurred_at"),
        Index("idx_correspondence_business_occurred", "business_id", "occurred_at"),
    )

    def __repr__(self):
        return (
            f"<Correspondence(id={self.id}, business_id={self.business_id}, "
            f"type='{self.correspondence_type}', occurred='{self.occurred_at}')>"
        )