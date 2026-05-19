from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Text, column

from app.clients.enums import ClientStatus
from app.common.soft_delete import SoftDeletableMixin
from app.database import Base
from app.utils.enum_utils import pg_enum
from app.utils.time_utils import utcnow


class ClientRecord(SoftDeletableMixin, Base):
    """Office CRM record and workflow anchor — one active record per legal entity."""

    __tablename__ = "client_records"

    id = Column(Integer, primary_key=True, autoincrement=True)

    legal_entity_id = Column(Integer, ForeignKey("legal_entities.id"), nullable=False, index=True)

    office_client_number = Column(Integer, nullable=True)
    accountant_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    status = Column(pg_enum(ClientStatus), nullable=False, default=ClientStatus.ACTIVE)
    notes = Column(Text, nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=utcnow)

    __table_args__ = (
        # One active ClientRecord per LegalEntity (soft-delete aware)
        Index(
            "ix_client_records_legal_entity_id_active",
            "legal_entity_id",
            unique=True,
            postgresql_where=column("deleted_at").is_(None),
            sqlite_where=column("deleted_at").is_(None),
        ),
        Index(
            "ix_client_records_office_client_number_active",
            "office_client_number",
            unique=True,
            postgresql_where=column("deleted_at").is_(None),
            sqlite_where=column("deleted_at").is_(None),
        ),
        Index(
            "ix_client_records_active_created_desc",
            created_at.desc(),
            postgresql_where=column("deleted_at").is_(None),
            sqlite_where=column("deleted_at").is_(None),
        ),
    )

    def __repr__(self) -> str:
        return f"<ClientRecord(id={self.id}, legal_entity_id={self.legal_entity_id}, status='{self.status}')>"
