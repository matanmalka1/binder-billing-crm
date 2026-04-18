from typing import Optional

from sqlalchemy.orm import Session

from app.binders.models.binder_intake_edit_log import BinderIntakeEditLog
from app.utils.time_utils import utcnow


class BinderIntakeEditLogRepository:
    """Data access layer for BinderIntakeEditLog records."""

    def __init__(self, db: Session):
        self.db = db

    def append(
        self,
        intake_id: int,
        field_name: str,
        old_value: Optional[str],
        new_value: Optional[str],
        changed_by: int,
    ) -> BinderIntakeEditLog:
        log = BinderIntakeEditLog(
            intake_id=intake_id,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            changed_by=changed_by,
            changed_at=utcnow(),
        )
        self.db.add(log)
        self.db.flush()
        return log

    def list_by_intake(self, intake_id: int) -> list[BinderIntakeEditLog]:
        return (
            self.db.query(BinderIntakeEditLog)
            .filter(BinderIntakeEditLog.intake_id == intake_id)
            .order_by(BinderIntakeEditLog.changed_at.asc())
            .all()
        )
