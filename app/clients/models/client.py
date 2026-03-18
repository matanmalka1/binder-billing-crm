from enum import Enum as PyEnum

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, String, Text
from app.utils.enum_utils import pg_enum

from app.database import Base
from app.utils.time_utils import utcnow


class ClientType(str, PyEnum):
    OSEK_PATUR = "osek_patur"
    OSEK_MURSHE = "osek_murshe"
    COMPANY = "company"
    EMPLOYEE = "employee"


class ClientStatus(str, PyEnum):
    ACTIVE = "active"
    FROZEN = "frozen"
    CLOSED = "closed"


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String, nullable=False)
    id_number = Column(String, nullable=False, index=True)
    client_type = Column(pg_enum(ClientType), nullable=False)
    status = Column(pg_enum(ClientStatus), default=ClientStatus.ACTIVE, nullable=False)
    primary_binder_number = Column(String, unique=True, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    # Structured address fields
    address_street = Column(String, nullable=True)
    address_building_number = Column(String, nullable=True)
    address_apartment = Column(String, nullable=True)
    address_city = Column(String, nullable=True)
    address_zip_code = Column(String, nullable=True)
    opened_at = Column(Date, nullable=False)
    closed_at = Column(Date, nullable=True)
    updated_at = Column(DateTime, nullable=True, onupdate=utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        # Partial unique index: only one active (non-deleted) client per id_number.
        # PostgreSQL supports WHERE clauses; SQLite falls back to a plain index.
        Index(
            "ix_clients_id_number_active",
            "id_number",
            unique=True,
            postgresql_where=Column("deleted_at").is_(None),
        ),
    )

    def __repr__(self):
        return f"<Client(id={self.id}, name='{self.full_name}', status='{self.status}')>"