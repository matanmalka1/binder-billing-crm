from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from app.utils.time import utcnow

from app.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    charge_id = Column(
        Integer,
        ForeignKey("charges.id"),
        nullable=False,
        unique=True,
        index=True
    )
    provider = Column(String, nullable=False)
    external_invoice_id = Column(String, nullable=False)
    document_url = Column(String, nullable=True)
    issued_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    def __repr__(self):
        return (
            f"<Invoice(id={self.id}, charge_id={self.charge_id}, "
            f"external_id='{self.external_invoice_id}')>"
        )
