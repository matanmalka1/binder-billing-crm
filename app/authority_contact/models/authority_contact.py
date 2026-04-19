"""
Authority Contact — a named contact at a government authority (רשות מסים, ביטוח לאומי, etc.)

Israeli context:
  Tax advisors maintain personal contacts at the Tax Authority (פקיד שומה),
  VAT branches (סניף מע"מ), and National Insurance (ביטוח לאומי).
  These contacts are referenced in correspondence entries and used when
  filing objections or scheduling hearings.

AuthorityContactLink — many-to-many between contacts and clients/businesses.

  A contact can serve multiple clients (e.g. same assessing officer handles
  several of the advisor's clients in the same district).
  A client can have multiple contacts (one per authority type).
  business_id is optional — some contacts are relevant to all businesses
  under a client; others are specific to one business (e.g. VAT branch for
  the company only).

Design decisions:
- AuthorityContact.business_id: primary association (the business that
  "owns" this contact record). AuthorityContactLink handles sharing.
- UniqueConstraint on (contact_id, client_id, business_id) prevents duplicate links.
  business_id=NULL is a valid distinct value in this constraint (PostgreSQL/SQLite).
- No soft delete on AuthorityContactLink — links are simply deleted when removed.
- updated_at on AuthorityContact — contact details (phone, office) change over time.
"""

from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from app.utils.enum_utils import pg_enum

from app.database import Base
from app.utils.time_utils import utcnow


class ContactType(str, PyEnum):
    ASSESSING_OFFICER  = "assessing_officer"   # פקיד שומה
    VAT_BRANCH         = "vat_branch"           # סניף מע"מ
    NATIONAL_INSURANCE = "national_insurance"   # ביטוח לאומי
    OTHER              = "other"


class AuthorityContact(Base):
    __tablename__ = "authority_contacts"

    id        = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    client_record_id = Column(Integer, ForeignKey("client_records.id"), nullable=True, index=True)

    # ── Contact identity ──────────────────────────────────────────────────────
    contact_type = Column(pg_enum(ContactType), nullable=False)
    name         = Column(String, nullable=False)
    office       = Column(String, nullable=True)   # שם הסניף / המחלקה
    phone        = Column(String, nullable=True)
    email        = Column(String, nullable=True)
    notes        = Column(Text,   nullable=True)

    # ── Metadata ──────────────────────────────────────────────────────────────
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=utcnow)

    # ── Soft delete ───────────────────────────────────────────────────────────
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        Index("idx_authority_contact_client", "client_id"),
        Index("idx_authority_contact_type",   "contact_type"),
    )

    def __repr__(self):
        return (
            f"<AuthorityContact(id={self.id}, client_id={self.client_id}, "
            f"type='{self.contact_type}', name='{self.name}')>"
        )

