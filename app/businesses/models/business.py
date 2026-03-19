from enum import Enum as PyEnum

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, String, Text
from app.utils.enum_utils import pg_enum

from app.database import Base
from app.utils.time_utils import utcnow


class BusinessType(str, PyEnum):
    OSEK_PATUR = "osek_patur"
    OSEK_MURSHE = "osek_murshe"
    COMPANY = "company"
    EMPLOYEE = "employee"


class BusinessStatus(str, PyEnum):
    ACTIVE = "active"
    FROZEN = "frozen"
    CLOSED = "closed"


class Business(Base):
    """
    עסק ספציפי תחת לקוח.
    לקוח יכול להחזיק מספר עסקים (למשל עוסק מורשה + חברה בע"מ).
    כל הפעילות העסקית (דוחות, חיובים, מע"מ) משויכת לעסק, לא ללקוח.
    """
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # קשר ללקוח
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)

    # פרטי העסק
    business_name = Column(String, nullable=True)  # אופציונלי — אם ריק, מציגים שם הלקוח
    business_type = Column(pg_enum(BusinessType), nullable=False)
    status = Column(pg_enum(BusinessStatus), default=BusinessStatus.ACTIVE, nullable=False)

    # מספר קלסר ראשי
    primary_binder_number = Column(String, unique=True, nullable=True)

    # תאריכים
    opened_at = Column(Date, nullable=False)
    closed_at = Column(Date, nullable=True)

    # מטא
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=utcnow)

    # Soft delete
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    restored_at = Column(DateTime, nullable=True)
    restored_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        # שם עסק ייחודי לאותו לקוח (רק אם יש שם)
        Index(
            "ix_business_client_name_active",
            "client_id",
            "business_name",
            unique=True,
            postgresql_where=Column("business_name").isnot(None) & Column("deleted_at").is_(None),
            sqlite_where=Column("business_name").isnot(None) & Column("deleted_at").is_(None),
        ),
        Index("ix_business_status", "status"),
        Index("ix_business_client_id", "client_id"),
    )

    def __repr__(self):
        return (
            f"<Business(id={self.id}, client_id={self.client_id}, "
            f"name='{self.business_name}', type='{self.business_type}', status='{self.status}')>"
        )