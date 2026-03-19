from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base
from app.utils.time_utils import utcnow


class BinderStatusLog(Base):
    """
    Binder status change log.

    Every status transition is recorded: IN_OFFICE -> READY_FOR_PICKUP -> RETURNED.
    Used for auditing and tracking binders that were not collected for a long time.
    """
    __tablename__ = "binder_status_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    binder_id = Column(Integer, ForeignKey("binders.id"), nullable=False, index=True)
    old_status = Column(String, nullable=False)
    new_status = Column(String, nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    changed_at = Column(DateTime, default=utcnow, nullable=False)
    notes = Column(Text, nullable=True)

    def __repr__(self):
        return (
            f"<BinderStatusLog(id={self.id}, binder_id={self.binder_id}, "
            f"{self.old_status} -> {self.new_status})>"
        )
