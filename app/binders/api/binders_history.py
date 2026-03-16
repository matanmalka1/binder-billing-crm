from fastapi import APIRouter, Depends, HTTPException, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.binders.schemas.binder_extended import BinderHistoryEntry, BinderHistoryResponse
from app.binders.schemas.binder import BinderIntakeListResponse, BinderIntakeResponse
from app.binders.services.binder_history_service import BinderHistoryService
from app.binders.repositories.binder_intake_repository import BinderIntakeRepository
from app.binders.repositories.binder_repository import BinderRepository
from app.users.repositories.user_repository import UserRepository

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
            detail="הקלסר לא נמצא",
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


@router.get("/{binder_id}/intakes", response_model=BinderIntakeListResponse)
def get_binder_intakes(
    binder_id: int,
    db: DBSession,
    user: CurrentUser,
):
    """Get all material intakes for a binder."""
    binder_repo = BinderRepository(db)
    binder = binder_repo.get_by_id(binder_id)
    if not binder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="הקלסר לא נמצא",
        )

    intake_repo = BinderIntakeRepository(db)
    intakes = intake_repo.list_by_binder(binder_id)

    user_ids = {i.received_by for i in intakes}
    user_repo = UserRepository(db)
    user_name_map = {u.id: u.full_name for u in [user_repo.get_by_id(uid) for uid in user_ids] if u}

    return BinderIntakeListResponse(
        binder_id=binder_id,
        intakes=[
            BinderIntakeResponse(
                **{k: v for k, v in i.__dict__.items() if not k.startswith("_")},
                received_by_name=user_name_map.get(i.received_by),
            )
            for i in intakes
        ],
    )
