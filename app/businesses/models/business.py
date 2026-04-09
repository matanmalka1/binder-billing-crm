from enum import Enum as PyEnum

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, String, Text, column, and_
from sqlalchemy.orm import relationship
from app.utils.enum_utils import pg_enum

from app.database import Base
from app.utils.time_utils import utcnow


class BusinessType(str, PyEnum):
    OSEK_PATUR  = "osek_patur"   # עוסק פטור — exempt dealer activity
    OSEK_MURSHE = "osek_murshe"  # עוסק מורשה — authorized dealer activity
    COMPANY     = "company"      # חברה בע"מ — limited company activity
    EMPLOYEE    = "employee"     # שכיר — wage-earner activity


class BusinessStatus(str, PyEnum):
    ACTIVE = "active"
    FROZEN = "frozen"
    CLOSED = "closed"


class Business(Base):
    """
    A specific business under a client.

    A client can hold multiple businesses (for example: authorized dealer + limited company).
    All business activity (reports, charges, VAT, binders) is associated with the business.

    Contact details (email, phone):
    - official_email / official_phone = business-specific contact details (DB columns)
    - email / phone = properties with fallback to client details
    """
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Link to client.
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)

    # Relationship: lazy="select"; use explicit joinedload when needed.
    client = relationship("Client", foreign_keys=[client_id], lazy="select")

    # Business details.
    business_name = Column(String, nullable=False)   # required: every activity must have a name
    business_type = Column(pg_enum(BusinessType), nullable=False)
    tax_id_number   = Column(String(9), nullable=True)
    
    status = Column(
        pg_enum(BusinessStatus),
        default=BusinessStatus.ACTIVE,
        nullable=False,
    )
    # Dates.
    opened_at = Column(Date, nullable=False)
    closed_at = Column(Date, nullable=True)

    # Business-specific contact details.
    # ── פרטי קשר (של העסק, עם fallback ללקוח ב-property) ─────────────────
    phone = Column(String(20),  nullable=True)   
    email = Column(String(254), nullable=True)

    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)

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
        """
        Display name of the business.
        If business_name exists, return it.
        Otherwise, return the client name.
        """
        return self.business_name or (self.client.full_name if self.client else f"עסק #{self.id}")

    @property
    def contact_phone(self) -> str | None:
        """Business phone, with fallback to client phone."""
        return self.phone or (self.client.phone if self.client else None)

    @property
    def contact_email(self) -> str | None:
        """Business email, with fallback to client email."""
        return self.email or (self.client.email if self.client else None)

    def __repr__(self):
        return (
            f"<Business(id={self.id}, client_id={self.client_id}, "
            f"name='{self.business_name}', type='{self.business_type}', "
            f"status='{self.status}')>"
        )

    __table_args__ = (
        Index("ix_business_client_id", "client_id"),
        Index("ix_business_status", "status"),
        Index("ix_business_assigned",  "assigned_to"),
        Index(
            "ix_business_tax_id",
            "tax_id_number",
            unique=True,
            postgresql_where=and_(column("tax_id_number").isnot(None), column("deleted_at").is_(None)),
            sqlite_where=and_(column("tax_id_number").isnot(None), column("deleted_at").is_(None)),
        ),
        Index(
            "ix_business_client_name_active",
            "client_id",
            "business_name",
            unique=True,
            postgresql_where=and_(column("business_name").isnot(None), column("deleted_at").is_(None)),
            sqlite_where=and_(column("business_name").isnot(None), column("deleted_at").is_(None)),
        ),
    )
