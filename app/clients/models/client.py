from enum import Enum as PyEnum

from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Integer, String, Text

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
    id_number = Column(String, unique=True, nullable=False, index=True)
    client_type = Column(Enum(ClientType), nullable=False)
    status = Column(Enum(ClientStatus), default=ClientStatus.ACTIVE, nullable=False)
    primary_binder_number = Column(String, unique=True, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    # Legacy free-text address — kept for backward compatibility, do not use for new data
    address = Column(String, nullable=True)
    # Structured address fields (replaces `address`)
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

    def __repr__(self):
        return f"<Client(id={self.id}, name='{self.full_name}', status='{self.status}')>"