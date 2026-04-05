"""Routes: read-only audit trail queries."""

from fastapi import APIRouter, Depends

from app.audit.repositories.entity_audit_log_repository import EntityAuditLogRepository
from app.audit.schemas.entity_audit_log import EntityAuditLogResponse, EntityAuditTrailResponse
from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.users.repositories.user_repository import UserRepository

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get(
    "/{entity_type}/{entity_id}",
    response_model=EntityAuditTrailResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def get_entity_audit_trail(
    entity_type: str,
    entity_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    """Get the full audit trail for any audited entity."""
    audit_repo = EntityAuditLogRepository(db)
    user_repo = UserRepository(db)
    entries = audit_repo.get_audit_trail(entity_type, entity_id)
    user_ids = list({e.performed_by for e in entries})
    users = user_repo.list_by_ids(user_ids) if user_ids else []
    user_map = {u.id: u.full_name for u in users}
    items = []
    for e in entries:
        row = EntityAuditLogResponse.model_validate(e)
        row.performed_by_name = user_map.get(e.performed_by)
        items.append(row)
    return EntityAuditTrailResponse(items=items)
