from enum import Enum as PyEnum

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, String, Text
from app.utils.enum_utils import pg_enum

from app.database import Base
from app.utils.time_utils import utcnow
from app.businesses.models.business import BusinessStatus, BusinessType


# Backward-compatible aliases for legacy imports in tests/modules.
ClientType = BusinessType
ClientStatus = BusinessStatus


class Client(Base):
    """
    מייצג אדם / ישות משפטית ברמת הזהות בלבד.
    פרטים עסקיים (סוג עוסק, סטטוס, דוחות) נמצאים ב-Business.
    """
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # פרטי זהות
    full_name = Column(String, nullable=False)
    id_number = Column(String, nullable=False, index=True)  # ת.ז. / ח.פ

    # פרטי התקשרות
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)

    # כתובת
    address_street = Column(String, nullable=True)
    address_building_number = Column(String, nullable=True)
    address_apartment = Column(String, nullable=True)
    address_city = Column(String, nullable=True)
    address_zip_code = Column(String, nullable=True)

    # מטא
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=utcnow)

    # Legacy business fields kept nullable for backward compatibility.
    # New code should use app.businesses.models.Business.
    client_type = Column(pg_enum(BusinessType), nullable=True)
    status = Column(
        pg_enum(BusinessStatus),
        default=BusinessStatus.ACTIVE,
        nullable=True,
    )
    primary_binder_number = Column(String, unique=True, nullable=True)
    opened_at = Column(Date, nullable=True)
    closed_at = Column(Date, nullable=True)

    # Soft delete
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    restored_at = Column(DateTime, nullable=True)
    restored_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        # ת.ז. ייחודית בין לקוחות פעילים בלבד
        Index(
            "ix_clients_id_number_active",
            "id_number",
            unique=True,
            postgresql_where=Column("deleted_at").is_(None),
        ),
    )

    def __repr__(self):
        return f"<Client(id={self.id}, name='{self.full_name}', id_number='{self.id_number}')>"
