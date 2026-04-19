from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, UniqueConstraint
from app.database import Base
from app.utils.time_utils import utcnow
from app.utils.enum_utils import pg_enum


class PersonLegalEntityRole(str, PyEnum):
    OWNER = "owner"
    AUTHORIZED_SIGNATORY = "authorized_signatory"
    CONTROLLING_SHAREHOLDER = "controlling_shareholder"


class PersonLegalEntityLink(Base):
    """Associates a Person with a LegalEntity and captures the relationship role."""

    __tablename__ = "person_legal_entity_links"

    id = Column(Integer, primary_key=True, autoincrement=True)

    person_id = Column(Integer, ForeignKey("persons.id"), nullable=False, index=True)
    legal_entity_id = Column(Integer, ForeignKey("legal_entities.id"), nullable=False, index=True)
    role = Column(pg_enum(PersonLegalEntityRole), nullable=False, default=PersonLegalEntityRole.OWNER)

    created_at = Column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("person_id", "legal_entity_id", "role", name="uq_person_legal_entity_role"),
        Index("ix_person_legal_entity_links_legal_entity_id", "legal_entity_id"),
    )

    def __repr__(self) -> str:
        return f"<PersonLegalEntityLink(person_id={self.person_id}, legal_entity_id={self.legal_entity_id}, role='{self.role}')>"
