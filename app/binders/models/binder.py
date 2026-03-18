from enum import Enum as PyEnum

from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Integer, String, Text, Index
from app.utils.enum_utils import pg_enum

from app.database import Base
from app.utils.time_utils import utcnow


class BinderStatus(str, PyEnum):
    IN_OFFICE = "in_office"
    READY_FOR_PICKUP = "ready_for_pickup"
    RETURNED = "returned"


class BinderType(str, PyEnum):
    VAT = "vat"
    INCOME_TAX = "income_tax"
    NATIONAL_INSURANCE = "national_insurance"
    CAPITAL_DECLARATION = "capital_declaration"
    ANNUAL_REPORT = "annual_report"
    SALARY = "salary"
    BOOKKEEPING = "bookkeeping"
    OTHER = "other"


class Binder(Base):
    __tablename__ = "binders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    binder_number = Column(String, nullable=False)
    binder_type = Column(pg_enum(BinderType), nullable=False)
    received_at = Column(Date, nullable=False)
    returned_at = Column(Date, nullable=True)
    status = Column(pg_enum(BinderStatus), default=BinderStatus.IN_OFFICE, nullable=False)
    received_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    returned_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    pickup_person_name = Column(String, nullable=True)
    annual_report_id = Column(Integer, ForeignKey("annual_reports.id"), nullable=True, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        Index("idx_binder_status", "status"),
        Index("idx_binder_received_at", "received_at"),
        Index(
            "idx_active_binder_unique",
            "binder_number",
            unique=True,
            postgresql_where=(status != BinderStatus.RETURNED),
            sqlite_where=(status != BinderStatus.RETURNED),
        ),
    )

    def __repr__(self):
        return f"<Binder(id={self.id}, number='{self.binder_number}', status='{self.status}')>"
