from sqlalchemy import select
from sqlalchemy.orm import Session

from app.binders.models.binder_status_log import BinderStatusLog
from app.common.repositories.base_repository import BaseRepository


class BinderStatusLogRepository(BaseRepository[BinderStatusLog]):
    """Data access layer for BinderStatusLog entities."""

    def __init__(self, db: Session):
        self.db = db

    def append(
        self,
        binder_id: int,
        old_status: str,
        new_status: str,
        changed_by: int,
        notes: str | None = None,
    ) -> BinderStatusLog:
        """Append status change log entry."""
        log = BinderStatusLog(
            binder_id=binder_id,
            old_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
            notes=notes,
        )
        self.db.add(log)
        self.db.flush()
        return log

    def list_by_binder(self, binder_id: int) -> list[BinderStatusLog]:
        """Get all status logs for a binder."""
        return self.db.scalars(
            select(BinderStatusLog)
            .where(BinderStatusLog.binder_id == binder_id)
            .order_by(BinderStatusLog.changed_at.asc())
        ).all()

    def list_recent(self, limit: int = 20) -> list[BinderStatusLog]:
        return self.db.scalars(
            select(BinderStatusLog)
            .order_by(BinderStatusLog.changed_at.desc(), BinderStatusLog.id.desc())
            .limit(limit)
        ).all()
