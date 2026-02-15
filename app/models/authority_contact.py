from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text, Index

from app.database import Base
from app.utils.time import utcnow


class ContactType(str, PyEnum):
    ASSESSING_OFFICER = "assessing_officer"
    VAT_BRANCH = "vat_branch"
    NATIONAL_INSURANCE = "national_insurance"
    OTHER = "other"


class AuthorityContact(Base):
    __tablename__ = "authority_contacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    contact_type = Column(Enum(ContactType), nullable=False)

    # Contact details
    name = Column(String, nullable=False)
    office = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)

    # Metadata
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True)

    __table_args__ = (Index("idx_authority_contact_type", "contact_type"),)

    def __repr__(self):
        return (
            f"<AuthorityContact(id={self.id}, client_id={self.client_id}, "
            f"type='{self.contact_type}', name='{self.name}')>"
        )