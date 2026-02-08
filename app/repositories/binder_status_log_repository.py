from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models import BinderStatusLog


class BinderStatusLogRepository:
    """Data access layer for BinderStatusLog entities."""

    def __init__(self, db: Session):
        self.db = db

    def append(
        self,
        binder_id: int,
        old_status: str,
        new_status: str,
        changed_by: int,
        notes: Optional[str] = None,
    ) -> BinderStatusLog:
        """Append status change log entry."""
        log = BinderStatusLog(
            binder_id=binder_id,
            old_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
            changed_at=datetime.utcnow(),
            notes=notes,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def list_by_binder(self, binder_id: int) -> list[BinderStatusLog]:
        """Get all status logs for a binder."""
        return (
            self.db.query(BinderStatusLog)
            .filter(BinderStatusLog.binder_id == binder_id)
            .order_by(BinderStatusLog.changed_at.asc())
            .all()
        )