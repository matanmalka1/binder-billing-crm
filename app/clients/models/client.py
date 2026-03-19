from enum import Enum as PyEnum

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, String, Text
from app.utils.enum_utils import pg_enum

from app.database import Base
from app.utils.time_utils import utcnow

# ── Backward-compatible aliases ───────────────────────────────────────────────
# שמות ישנים שקוד legacy עדיין מייבא — מפנים למודל Business
from app.businesses.models.business import BusinessStatus, BusinessType

ClientType = BusinessType
ClientStatus = BusinessStatus


class Client(Base):
    """
    מייצג אדם / ישות משפטית ברמת הזהות בלבד.

    Client = מי האדם (שם, ת.ז., פרטי קשר, כתובת).
    Business = מה העסקים שלו (סוג, סטטוס, דוחות, חיובים).

    שדות legacy (client_type, status, primary_binder_number, opened_at, closed_at)
    נשמרים כ-nullable לתאימות SQLite בלבד.
    ב-PostgreSQL הם הוסרו במיגרציה e1f2a3b4c5d6.
    אין לקרוא או לכתוב לשדות אלה — יש להשתמש ב-Business.
    """
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── פרטי זהות ─────────────────────────────────────────────────────────────
    full_name = Column(String, nullable=False)
    id_number = Column(String, nullable=False, index=True)  # ת.ז. / ח.פ

    # ── פרטי התקשרות ──────────────────────────────────────────────────────────
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)

    # ── כתובת ─────────────────────────────────────────────────────────────────
    address_street = Column(String, nullable=True)
    address_building_number = Column(String, nullable=True)
    address_apartment = Column(String, nullable=True)
    address_city = Column(String, nullable=True)
    address_zip_code = Column(String, nullable=True)

    # ── מטא ───────────────────────────────────────────────────────────────────
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=utcnow)

    # ── Soft delete ────────────────────────────────────────────────────────────
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    restored_at = Column(DateTime, nullable=True)
    restored_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # ── Legacy fields — SQLite only ────────────────────────────────────────────
    # DEPRECATED: השתמש ב-Business.business_type במקום
    client_type = Column(pg_enum(BusinessType), nullable=True)

    # DEPRECATED: השתמש ב-Business.status במקום
    status = Column(
        pg_enum(BusinessStatus),
        nullable=True,
    )

    # DEPRECATED: אין שימוש — הוסר מהלוגיקה העסקית
    primary_binder_number = Column(String, unique=True, nullable=True)

    # DEPRECATED: השתמש ב-Business.opened_at במקום
    opened_at = Column(Date, nullable=True)

    # DEPRECATED: השתמש ב-Business.closed_at במקום
    closed_at = Column(Date, nullable=True)

    __table_args__ = (
        # ת.ז. ייחודית בין לקוחות פעילים בלבד
        Index(
            "ix_clients_id_number_active",
            "id_number",
            unique=True,
            postgresql_where="deleted_at IS NULL",
            sqlite_where="deleted_at IS NULL",
        ),
    )

    def __repr__(self):
        return (
            f"<Client(id={self.id}, name='{self.full_name}', "
            f"id_number='{self.id_number}')>"
        )