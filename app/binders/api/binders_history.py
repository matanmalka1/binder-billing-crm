from fastapi import APIRouter, Depends, HTTPException, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.binders.schemas.binder_extended import BinderHistoryEntry, BinderHistoryResponse
from app.binders.schemas.binder import BinderIntakeListResponse
from app.binders.services.binder_history_service import BinderHistoryService

router = APIRouter(
    prefix="/binders",
    tags=["binders-history"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get("/{binder_id}/history", response_model=BinderHistoryResponse)
def get_binder_history(binder_id: int, db: DBSession, user: CurrentUser):
    """Get audit history for a binder."""
    service = BinderHistoryService(db)
    result = service.get_binder_history(binder_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="הקלסר לא נמצא")

    binder, logs = result
    return BinderHistoryResponse(
        binder_id=binder.id,
        history=service.build_history_entries(logs),
    )


@router.get("/{binder_id}/intakes", response_model=BinderIntakeListResponse)
def get_binder_intakes(binder_id: int, db: DBSession, user: CurrentUser):
    """Get all material intakes for a binder."""
    service = BinderHistoryService(db)
    intakes = service.get_binder_intakes(binder_id)
    return BinderIntakeListResponse(binder_id=binder_id, intakes=intakes)