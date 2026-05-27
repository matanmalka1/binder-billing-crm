from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.time_utils import utcnow


class BinderIntakeEditLog(Base):
    """
    Field-level audit trail for edits to BinderIntake and its BinderIntakeMaterial rows.

    One record per changed field per edit operation. Records the old and new value
    as strings for human-readable audit display.
    """

    __tablename__ = "binder_intake_edit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # The intake that was edited.
    intake_id: Mapped[int] = mapped_column(
        ForeignKey("binder_intakes.id"),
        nullable=False,
        index=True,
    )

    # Name of the field that changed (e.g. "received_at", "notes", "business_id").
    field_name: Mapped[str] = mapped_column(String, nullable=False)

    # String representation of the value before the edit (None if field was unset).
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    # String representation of the value after the edit.
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    changed_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    def __repr__(self):
        return (
            f"<BinderIntakeEditLog(id={self.id}, intake_id={self.intake_id}, "
            f"field='{self.field_name}')>"
        )
