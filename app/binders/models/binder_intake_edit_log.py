from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base
from app.utils.time_utils import utcnow


class BinderIntakeEditLog(Base):
    """
    Field-level audit trail for edits to BinderIntake and its BinderIntakeMaterial rows.

    One record per changed field per edit operation. Records the old and new value
    as strings for human-readable audit display.
    """
    __tablename__ = "binder_intake_edit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # The intake that was edited.
    intake_id = Column(
        Integer, ForeignKey("binder_intakes.id"), nullable=False, index=True,
    )

    # Name of the field that changed (e.g. "received_at", "notes", "business_id").
    field_name = Column(String, nullable=False)

    # String representation of the value before the edit (None if field was unset).
    old_value = Column(Text, nullable=True)

    # String representation of the value after the edit.
    new_value = Column(Text, nullable=True)

    changed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    changed_at = Column(DateTime, default=utcnow, nullable=False)

    def __repr__(self):
        return (
            f"<BinderIntakeEditLog(id={self.id}, intake_id={self.intake_id}, "
            f"field='{self.field_name}')>"
        )
