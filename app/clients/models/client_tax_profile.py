from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, Integer, String

from app.database import Base
from app.utils.time import utcnow


class VatType(str, PyEnum):
    MONTHLY = "monthly"
    BIMONTHLY = "bimonthly"
    EXEMPT = "exempt"


class ClientTaxProfile(Base):
    __tablename__ = "client_tax_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(
        Integer, ForeignKey("clients.id"), nullable=False, unique=True, index=True
    )
    vat_type = Column(Enum(VatType), nullable=True)
    business_type = Column(String, nullable=True)
    tax_year_start = Column(Integer, nullable=True)
    accountant_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return (
            f"<ClientTaxProfile(id={self.id}, client_id={self.client_id}, "
            f"vat_type='{self.vat_type}')>"
        )
