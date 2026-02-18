import json
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.users.models.user_audit_log import AuditAction, AuditStatus, UserAuditLog


class UserAuditLogRepository:
    """Data access layer for user audit logs."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        action: AuditAction,
        status: AuditStatus,
        actor_user_id: Optional[int] = None,
        target_user_id: Optional[int] = None,
        email: Optional[str] = None,
        reason: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> UserAuditLog:
        log = UserAuditLog(
            action=action,
            status=status,
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            email=email,
            reason=reason,
            metadata_json=json.dumps(metadata) if metadata is not None else None,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def list(
        self,
        page: int = 1,
        page_size: int = 20,
        action: Optional[AuditAction] = None,
        target_user_id: Optional[int] = None,
        actor_user_id: Optional[int] = None,
        email: Optional[str] = None,
        from_ts: Optional[datetime] = None,
        to_ts: Optional[datetime] = None,
    ) -> list[UserAuditLog]:
        query = self._build_query(
            action=action,
            target_user_id=target_user_id,
            actor_user_id=actor_user_id,
            email=email,
            from_ts=from_ts,
            to_ts=to_ts,
        )
        offset = (page - 1) * page_size
        return query.order_by(UserAuditLog.created_at.desc()).offset(offset).limit(page_size).all()

    def count(
        self,
        action: Optional[AuditAction] = None,
        target_user_id: Optional[int] = None,
        actor_user_id: Optional[int] = None,
        email: Optional[str] = None,
        from_ts: Optional[datetime] = None,
        to_ts: Optional[datetime] = None,
    ) -> int:
        return self._build_query(
            action=action,
            target_user_id=target_user_id,
            actor_user_id=actor_user_id,
            email=email,
            from_ts=from_ts,
            to_ts=to_ts,
        ).count()

    def _build_query(
        self,
        action: Optional[AuditAction],
        target_user_id: Optional[int],
        actor_user_id: Optional[int],
        email: Optional[str],
        from_ts: Optional[datetime],
        to_ts: Optional[datetime],
    ):
        query = self.db.query(UserAuditLog)
        if action is not None:
            query = query.filter(UserAuditLog.action == action)
        if target_user_id is not None:
            query = query.filter(UserAuditLog.target_user_id == target_user_id)
        if actor_user_id is not None:
            query = query.filter(UserAuditLog.actor_user_id == actor_user_id)
        if email is not None:
            query = query.filter(UserAuditLog.email == email)
        if from_ts is not None:
            query = query.filter(UserAuditLog.created_at >= from_ts)
        if to_ts is not None:
            query = query.filter(UserAuditLog.created_at <= to_ts)
        return query

