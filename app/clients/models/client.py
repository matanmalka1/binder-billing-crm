from enum import Enum as PyEnum

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, column
from app.utils.enum_utils import pg_enum

from app.database import Base
from app.utils.time_utils import utcnow
from app.common.enums import EntityType, VatType

class IdNumberType(str, PyEnum):
    INDIVIDUAL   = "individual"   # ת"ז — 9 ספרות עם ספרת ביקורת
    CORPORATION  = "corporation"  # ח"פ — 9 ספרות
    PASSPORT     = "passport"     # דרכון — לתושבי חוץ
    OTHER        = "other"

class ClientStatus(str, PyEnum):
    ACTIVE = "active"
    FROZEN = "frozen"
    CLOSED = "closed"

class Client(Base):
    """
    Represents a person / legal entity at the identity level only.

    Client = who the person is (name, ID number, contact details, address).
    Business = what their businesses are (type, status, reports, charges).

    Legacy fields (client_type, status, primary_binder_number, opened_at, closed_at)
    are kept nullable for SQLite compatibility only.
    In PostgreSQL they were removed in migration e1f2a3b4c5d6.
    Do not read or write these fields — use Business instead.
    """
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── Identity details ──────────────────────────────────────────────────────
    full_name = Column(String, nullable=False)
    id_number = Column(String, nullable=False, index=True)  # ID number / company ID
    id_number_type = Column(pg_enum(IdNumberType), nullable=False, 
                            default=IdNumberType.INDIVIDUAL)
    # ── Contact details ───────────────────────────────────────────────────────
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)

    # ── Address ───────────────────────────────────────────────────────────────
    address_street = Column(String, nullable=True)
    address_building_number = Column(String, nullable=True)
    address_apartment = Column(String, nullable=True)
    address_city = Column(String, nullable=True)
    address_zip_code = Column(String, nullable=True)

    # ── Legal / tax entity classification ────────────────────────────────────
    # The type of legal entity this client represents.
    # OSEK_PATUR / OSEK_MURSHE = individual; COMPANY_LTD = separate legal entity; EMPLOYEE = wage earner.
    entity_type = Column(pg_enum(EntityType), nullable=True)

    # ── Tax reporting ─────────────────────────────────────────────────────────
    # Authoritative VAT reporting frequency (monthly/bimonthly/exempt).
    # NULL means not yet configured; service layer defaults to BIMONTHLY for OSEK_MURSHE.
    vat_reporting_frequency = Column(pg_enum(VatType), nullable=True)

    # ── Tax profile (formerly BusinessTaxProfile) ─────────────────────────────
    vat_start_date          = Column(Date,            nullable=True)
    vat_exempt_ceiling      = Column(Numeric(12, 0),  nullable=True)   # תקרת פטור ממע"מ
    advance_rate            = Column(Numeric(5, 2),   nullable=True)   # שיעור מקדמות
    advance_rate_updated_at = Column(Date,            nullable=True)
    accountant_name         = Column(String(100),     nullable=True)   # שם רואה החשבון
    business_type_label     = Column(String(100),     nullable=True)   # סוג עסק (טקסט חופשי)
    fiscal_year_start_month = Column(Integer,         nullable=False,  server_default="1")
    tax_year_start          = Column(Integer,         nullable=True)   # שנת מס התחלה
    business_start_date     = Column(Date,            nullable=True)   # תאריך הקמת העסק

    # ── Metadata ──────────────────────────────────────────────────────────────
    status = Column(pg_enum(ClientStatus), nullable=False, default=ClientStatus.ACTIVE)

    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=utcnow)

    # ── Soft delete ────────────────────────────────────────────────────────────
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    restored_at = Column(DateTime, nullable=True)
    restored_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        # Unique ID number among active clients only
        Index(
            "ix_clients_id_number_active",
            "id_number",
            unique=True,
            postgresql_where=column("deleted_at").is_(None),
            sqlite_where=column("deleted_at").is_(None),
        ),
        Index("ix_clients_full_name", "full_name"),
    )

    def __repr__(self):
        return (
            f"<Client(id={self.id}, name='{self.full_name}', "
            f"id_number='{self.id_number}')>"
        )
