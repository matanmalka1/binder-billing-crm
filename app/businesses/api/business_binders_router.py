from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.binders.schemas.binder_extended import (
    BinderDetailResponse,
    BinderListResponseExtended,
)
from app.binders.services.binder_operations_service import BinderOperationsService
from app.businesses.repositories.business_repository import BusinessRepository

router = APIRouter(
    prefix="/businesses",
    tags=["businesses-binders"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get("/{business_id}/binders", response_model=BinderListResponseExtended)
def list_business_binders(
    business_id: int,
    db: DBSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    List all binders for a specific business.

    Note: Binders belong to clients, not businesses. This endpoint resolves
    the client that owns the business and returns that client's binders.
    """
    
    business = BusinessRepository(db).get_by_id(business_id)
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="העסק לא נמצא",
        )

    service = BinderOperationsService(db)
    items, total = service.get_client_binders(
        client_id=business.client_id,
        page=page,
        page_size=page_size,
    )

    enriched = [
        BinderDetailResponse(**service.enrich_binder(b))
        for b in items
    ]

    return BinderListResponseExtended(
        items=enriched,
        page=page,
        page_size=page_size,
        total=total,
    )