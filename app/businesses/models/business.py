from enum import Enum as PyEnum

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, String, Text, column, and_
from sqlalchemy.orm import relationship
from app.utils.enum_utils import pg_enum

from app.database import Base
from app.utils.time_utils import utcnow


class BusinessStatus(str, PyEnum):
    ACTIVE = "active"
    FROZEN = "frozen"
    CLOSED = "closed"


class Business(Base):
    """
    A specific business under a client.

    A client can hold multiple businesses (multiple operational activities under the same legal entity).
    Business-scoped records may reference this model directly, while tax/reporting workflows that are
    legally scoped to the client keep their primary ownership on Client and may only tag individual
    records to a business.

    Contact override columns are persisted here. Owner fallback is resolved in the service layer.
    """
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, autoincrement=True)

    legal_entity_id = Column(Integer, ForeignKey("legal_entities.id"), nullable=True, index=True)

    legal_entity = relationship(
        "LegalEntity",
        foreign_keys=[legal_entity_id],
        lazy="select",
        viewonly=True,
    )

    # Business details.
    business_name = Column(String, nullable=False)   # required: every activity must have a name
    status = Column(
        pg_enum(BusinessStatus),
        default=BusinessStatus.ACTIVE,
        nullable=False,
    )
    # Dates.
    opened_at = Column(Date, nullable=False)
    closed_at = Column(Date, nullable=True)

    # Business-specific contact overrides.
    phone_override = Column(String(20), nullable=True)
    email_override = Column(String(254), nullable=True)

    # Metadata.
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=utcnow)

    # Soft delete
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    restored_at = Column(DateTime, nullable=True)
    restored_by = Column(Integer, ForeignKey("users.id"), nullable=True)


    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def full_name(self) -> str:
        if self.business_name:
            return self.business_name
        if self.legal_entity:
            return self.legal_entity.official_name
        return ""

    def __repr__(self):
        return (
            f"<Business(id={self.id}, legal_entity_id={self.legal_entity_id}, "
            f"name='{self.business_name}', status='{self.status}')>"
        )

    __table_args__ = (
        Index("ix_business_status", "status"),
        Index(
            "ix_business_legal_entity_name_active",
            "legal_entity_id",
            "business_name",
            unique=True,
            postgresql_where=and_(column("business_name").isnot(None), column("deleted_at").is_(None)),
            sqlite_where=and_(column("business_name").isnot(None), column("deleted_at").is_(None)),
        ),
    )
