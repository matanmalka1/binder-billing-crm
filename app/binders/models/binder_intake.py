from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Text

from app.database import Base
from app.utils.time_utils import utcnow


class BinderIntake(Base):
    __tablename__ = "binder_intakes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    binder_id = Column(Integer, ForeignKey("binders.id"), nullable=False, index=True)
    received_at = Column(Date, nullable=False)
    received_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    def __repr__(self):
        return f"<BinderIntake(id={self.id}, binder_id={self.binder_id}, received_at='{self.received_at}')>"
