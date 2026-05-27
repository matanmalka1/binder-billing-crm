from sqlalchemy import select
from sqlalchemy.orm import Session

from app.binders.models.binder_lifecycle_log import BinderLifecycleLog
from app.common.repositories.base_repository import BaseRepository


class BinderLifecycleLogRepository(BaseRepository[BinderLifecycleLog]):
    """Data access layer for BinderLifecycleLog entities."""

    model = BinderLifecycleLog

    def __init__(self, db: Session):
        super().__init__(db)

    def append(
        self,
        binder_id: int,
        field_name: str,
        old_value: str,
        new_value: str,
        changed_by_user_id: int,
        notes: str | None = None,
    ) -> BinderLifecycleLog:
        """Append lifecycle field change log entry."""
        log = BinderLifecycleLog(
            binder_id=binder_id,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            changed_by_user_id=changed_by_user_id,
            notes=notes,
        )
        self.db.add(log)
        self.db.flush()
        return log

    def list_by_binder(self, binder_id: int) -> list[BinderLifecycleLog]:
        """Get all lifecycle logs for a binder."""
        return self.db.scalars(
            select(BinderLifecycleLog)
            .where(BinderLifecycleLog.binder_id == binder_id)
            .order_by(BinderLifecycleLog.changed_at.asc(), BinderLifecycleLog.id.asc())
        ).all()

    def list_recent(self, limit: int = 20) -> list[BinderLifecycleLog]:
        return self.db.scalars(
            select(BinderLifecycleLog)
            .order_by(BinderLifecycleLog.changed_at.desc(), BinderLifecycleLog.id.desc())
            .limit(limit)
        ).all()
