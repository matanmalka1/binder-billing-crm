from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.schema import CheckConstraint
from app.utils.enum_utils import pg_enum

from app.database import Base
from app.utils.time_utils import utcnow


class ContactType(str, PyEnum):
    ASSESSING_OFFICER = "assessing_officer"   # פקיד שומה
    VAT_BRANCH = "vat_branch"                 # סניף מע"מ
    NATIONAL_INSURANCE = "national_insurance"  # ביטוח לאומי
    OTHER = "other"


class AuthorityContact(Base):
    """
    איש קשר ברשות המסים — ישות עצמאית.
    יכול להיות מקושר למספר לקוחות / עסקים דרך AuthorityContactLink.
    """
    __tablename__ = "authority_contacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contact_type = Column(pg_enum(ContactType), nullable=False)

    # פרטי איש הקשר
    name = Column(String, nullable=False)
    office = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    # מטא
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=utcnow)

    # Soft delete
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        Index("idx_authority_contact_type", "contact_type"),
    )

    def __repr__(self):
        return (
            f"<AuthorityContact(id={self.id}, type='{self.contact_type}', "
            f"name='{self.name}')>"
        )


class AuthorityContactLink(Base):
    """
    קישור בין איש קשר ברשות לבין לקוח / עסק.
    
    ברירת מחדל: קישור ברמת לקוח (client_id חובה).
    חריג: ניתן לקשר גם לעסק ספציפי (business_id אופציונלי).
    
    דוגמה:
    - פקיד שומה → לקוח (מטפל בכל עסקי הלקוח)
    - פקיד מע"מ → לקוח + עסק ספציפי (מטפל רק בחברה בע"מ)
    """
    __tablename__ = "authority_contact_links"

    id = Column(Integer, primary_key=True, autoincrement=True)

    contact_id = Column(
        Integer, ForeignKey("authority_contacts.id"), nullable=False, index=True
    )
    client_id = Column(
        Integer, ForeignKey("clients.id"), nullable=False, index=True
    )
    business_id = Column(
        Integer, ForeignKey("businesses.id"), nullable=True, index=True
    )

    created_at = Column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        # מניעת כפילויות
        Index(
            "ix_authority_contact_link_unique",
            "contact_id", "client_id", "business_id",
            unique=True,
        ),
    )

    def __repr__(self):
        return (
            f"<AuthorityContactLink(contact_id={self.contact_id}, "
            f"client_id={self.client_id}, business_id={self.business_id})>"
        )