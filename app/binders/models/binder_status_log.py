from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.time_utils import utcnow


class BinderStatusLog(Base):
    """
    Binder status change log.
    Every status transition is recorded, including flows such as
    IN_OFFICE -> CLOSED_IN_OFFICE -> READY_FOR_PICKUP -> RETURNED.
    Used for auditing and tracking binders that were not collected for a long time.
    """

    __tablename__ = "binder_status_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    binder_id: Mapped[int] = mapped_column(ForeignKey("binders.id"), nullable=False, index=True)
    old_status: Mapped[str] = mapped_column(String, nullable=False)
    new_status: Mapped[str] = mapped_column(String, nullable=False)
    changed_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self):
        return (
            f"<BinderStatusLog(id={self.id}, binder_id={self.binder_id}, "
            f"{self.old_status} -> {self.new_status})>"
        )
