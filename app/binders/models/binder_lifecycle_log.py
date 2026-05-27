from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.time_utils import utcnow


class BinderLifecycleLog(Base):
    """
    Binder lifecycle field change log.
    Every lifecycle transition records one row per changed field.
    """

    __tablename__ = "binder_lifecycle_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    binder_id: Mapped[int] = mapped_column(ForeignKey("binders.id"), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String, nullable=False)
    old_value: Mapped[str] = mapped_column(String, nullable=False)
    new_value: Mapped[str] = mapped_column(String, nullable=False)
    changed_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self):
        return (
            f"<BinderLifecycleLog(id={self.id}, binder_id={self.binder_id}, "
            f"{self.field_name}: {self.old_value} -> {self.new_value})>"
        )
