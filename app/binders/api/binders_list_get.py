from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.binders.schemas.binder import BinderListResponse, BinderResponse
from app.binders.services.binder_service import BinderService
from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole

router = APIRouter(
    prefix="/binders",
    tags=["binders"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get("", response_model=BinderListResponse)
def list_binders(
    db: DBSession,
    user: CurrentUser,
    status_filter: Optional[str] = Query(None, alias="status"),
    business_id: Optional[int] = None,
    work_state: Optional[str] = None,
    query: Optional[str] = None,
    client_name: Optional[str] = None,
    binder_number: Optional[str] = None,
    year: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: Optional[str] = Query(None),
    sort_dir: str = Query("desc"),
):
    """List active binders with optional filters, sorting, and pagination."""
    service = BinderService(db)
    items, total = service.list_binders_enriched(
        business_id=business_id,
        status=status_filter,
        work_state=work_state,
        query=query,
        client_name_filter=client_name,
        binder_number=binder_number,
        year=year,
        sort_by=sort_by or "received_at",
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )
    return BinderListResponse(items=items, page=page, page_size=page_size, total=total)


@router.get("/{binder_id}", response_model=BinderResponse)
def get_binder(binder_id: int, db: DBSession, user: CurrentUser):
    """Get binder by ID."""
    service = BinderService(db)
    binder_response = service.get_binder_with_business_name(binder_id)
    if not binder_response:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="הקלסר לא נמצא")
    return binder_response


@router.delete(
    "/{binder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def delete_binder(binder_id: int, db: DBSession, user: CurrentUser):
    """Soft-delete a binder (ADVISOR only)."""
    service = BinderService(db)
    deleted = service.delete_binder(binder_id, actor_id=user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="הקלסר לא נמצא")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
