from enum import Enum as PyEnum

from sqlalchemy import Column,Date, DateTime, ForeignKey, Integer, Numeric, String
from app.utils.enum_utils import pg_enum

from app.database import Base
from app.utils.time_utils import utcnow


class VatType(str, PyEnum):
    MONTHLY = "monthly"
    BIMONTHLY = "bimonthly"
    EXEMPT = "exempt"


class BusinessTaxProfile(Base):
    """
    פרופיל מס של עסק ספציפי.
    כל עסק מחזיק פרופיל מס נפרד (סוג מע"מ, שיעור מקדמות וכו').
    שינוי שם מ-ClientTaxProfile ל-BusinessTaxProfile.
    """
    __tablename__ = "business_tax_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(
        Integer, ForeignKey("businesses.id"), nullable=False, unique=True, index=True
    )

    vat_type = Column(pg_enum(VatType), nullable=True)
    vat_start_date = Column(Date, nullable=True)
    accountant_name = Column(String(100), nullable=True)
    vat_exempt_ceiling = Column(Numeric(12, 0), nullable=True)
    advance_rate = Column(Numeric(5, 2), nullable=True)
    advance_rate_updated_at = Column(Date, nullable=True)

    fiscal_year_start_month = Column(Integer, nullable=False, default=1)

    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=utcnow)

    def __repr__(self):
        return (
            f"<BusinessTaxProfile(id={self.id}, business_id={self.business_id}, "
            f"vat_type='{self.vat_type}')>"
        )