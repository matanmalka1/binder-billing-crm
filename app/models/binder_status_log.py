from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base


class BinderStatusLog(Base):
    __tablename__ = "binder_status_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    binder_id = Column(Integer, ForeignKey("binders.id"), nullable=False, index=True)
    old_status = Column(String, nullable=False)
    new_status = Column(String, nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    notes = Column(Text, nullable=True)

    def __repr__(self):
        return (
            f"<BinderStatusLog(id={self.id}, binder_id={self.binder_id}, "
            f"{self.old_status} -> {self.new_status})>"
        )