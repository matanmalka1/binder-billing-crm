from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils.time_utils import utcnow
 

class BinderIntake(Base):
    """
    Material intake event for a binder.

    Every time a client brings materials to the office, an intake event is recorded.
    Each event can include multiple items of different types
    and for different businesses (BinderIntakeMaterial).
    """
    __tablename__ = "binder_intakes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    binder_id = Column(Integer, ForeignKey("binders.id", ondelete="CASCADE"), nullable=False, index=True)

    binder = relationship("Binder", back_populates="intakes")

    # When the material was received.
    received_at = Column(Date, nullable=False)

    # Who received the material at the office.
    received_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # General notes about the event ("arrived with an envelope", "some material is missing").
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utcnow, nullable=False)
    def __repr__(self):
        return (
            f"<BinderIntake(id={self.id}, binder_id={self.binder_id}, "
            f"received_at='{self.received_at}')>"
        )
