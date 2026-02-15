from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models import AuditAction, AuditStatus
from app.repositories import UserAuditLogRepository


class AuditLogService:
    """Audit log orchestration for authentication and user actions."""

    def __init__(self, db: Session):
        self.repo = UserAuditLogRepository(db)

    def log(
        self,
        action: AuditAction,
        status: AuditStatus,
        actor_user_id: Optional[int] = None,
        target_user_id: Optional[int] = None,
        email: Optional[str] = None,
        reason: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        self.repo.create(
            action=action,
            status=status,
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            email=email,
            reason=reason,
            metadata=metadata,
        )

    def list_logs(
        self,
        page: int = 1,
        page_size: int = 20,
        action: Optional[AuditAction] = None,
        target_user_id: Optional[int] = None,
        actor_user_id: Optional[int] = None,
        email: Optional[str] = None,
        from_ts: Optional[datetime] = None,
        to_ts: Optional[datetime] = None,
    ):
        items = self.repo.list(
            page=page,
            page_size=page_size,
            action=action,
            target_user_id=target_user_id,
            actor_user_id=actor_user_id,
            email=email,
            from_ts=from_ts,
            to_ts=to_ts,
        )
        total = self.repo.count(
            action=action,
            target_user_id=target_user_id,
            actor_user_id=actor_user_id,
            email=email,
            from_ts=from_ts,
            to_ts=to_ts,
        )
        return items, total

