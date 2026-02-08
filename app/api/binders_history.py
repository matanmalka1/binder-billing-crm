from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUser, DBSession, require_role
from app.models import UserRole
from app.schemas.binder_extended import BinderHistoryEntry, BinderHistoryResponse
from app.services.binder_history_service import BinderHistoryService

router = APIRouter(
    prefix="/binders",
    tags=["binders-history"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get("/{binder_id}/history", response_model=BinderHistoryResponse)
def get_binder_history(
    binder_id: int,
    db: DBSession,
    user: CurrentUser,
):
    """Get audit history for a binder."""
    service = BinderHistoryService(db)
    result = service.get_binder_history(binder_id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Binder not found",
        )
    
    binder, logs = result
    
    history_entries = [
        BinderHistoryEntry(
            old_status=log.old_status,
            new_status=log.new_status,
            changed_by=log.changed_by,
            changed_at=log.changed_at.isoformat(),
            notes=log.notes,
        )
        for log in logs
    ]
    
    return BinderHistoryResponse(
        binder_id=binder.id,
        history=history_entries,
    )
