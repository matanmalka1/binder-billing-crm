import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.users.models.user_audit_log import AuditAction
from app.users.models.user_management import UserAuditLogListResponse, UserAuditLogResponse
from app.users.services.audit_log_service import AuditLogService

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)


@router.get("/audit-logs", response_model=UserAuditLogListResponse)
def list_audit_logs(
    db: DBSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: Optional[AuditAction] = None,
    target_user_id: Optional[int] = None,
    actor_user_id: Optional[int] = None,
    email: Optional[str] = None,
    from_ts: Optional[datetime] = Query(None, alias="from"),
    to_ts: Optional[datetime] = Query(None, alias="to"),
):
    service = AuditLogService(db)
    items, total = service.list_logs(
        page=page,
        page_size=page_size,
        action=action,
        target_user_id=target_user_id,
        actor_user_id=actor_user_id,
        email=email,
        from_ts=from_ts,
        to_ts=to_ts,
    )
    response_items = [
        UserAuditLogResponse(
            id=item.id,
            action=item.action,
            actor_user_id=item.actor_user_id,
            target_user_id=item.target_user_id,
            email=item.email,
            status=item.status,
            reason=item.reason,
            metadata=json.loads(item.metadata_json) if item.metadata_json else None,
            created_at=item.created_at,
        )
        for item in items
    ]
    return UserAuditLogListResponse(
        items=response_items,
        page=page,
        page_size=page_size,
        total=total,
    )
