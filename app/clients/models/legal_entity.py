from sqlalchemy import Column, Date, DateTime, Index, Integer, Numeric, String, UniqueConstraint
from app.database import Base
from app.utils.time_utils import utcnow
from app.common.enums import EntityType, VatType, IdNumberType
from app.utils.enum_utils import pg_enum


class LegalEntity(Base):
    """Legal and tax identity of a registered entity (sole trader, company, etc.)."""

    __tablename__ = "legal_entities"

    id = Column(Integer, primary_key=True, autoincrement=True)

    id_number = Column(String, nullable=False)
    id_number_type = Column(pg_enum(IdNumberType), nullable=False)
    entity_type = Column(pg_enum(EntityType), nullable=True)

    vat_reporting_frequency = Column(pg_enum(VatType), nullable=True)
    vat_exempt_ceiling = Column(Numeric(12, 0), nullable=True)
    advance_rate = Column(Numeric(5, 2), nullable=True)
    advance_rate_updated_at = Column(Date, nullable=True)

    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=utcnow)

    __table_args__ = (
        UniqueConstraint("id_number_type", "id_number", name="uq_legal_entity_registration_id"),
    )

    def __repr__(self) -> str:
        return f"<LegalEntity(id={self.id}, id_number='{self.id_number}', entity_type='{self.entity_type}')>"
