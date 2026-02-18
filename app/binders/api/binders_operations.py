from fastapi import APIRouter, Depends, Query

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.schemas.binder_extended import (
    BinderDetailResponse,
    BinderListResponseExtended,
)
from app.binders.services.binder_operations_service import BinderOperationsService

router = APIRouter(
    prefix="/binders",
    tags=["binders-operations"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get("/open", response_model=BinderListResponseExtended)
def list_open_binders(
    db: DBSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List open binders (status != RETURNED)."""
    service = BinderOperationsService(db)
    items, total = service.get_open_binders(page=page, page_size=page_size)
    
    enriched = [
        BinderDetailResponse(**service.enrich_binder_with_sla(b, db))
        for b in items
    ]
    
    return BinderListResponseExtended(
        items=enriched,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/overdue", response_model=BinderListResponseExtended)
def list_overdue_binders(
    db: DBSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List overdue binders (expected_return_at < today, status != RETURNED)."""
    service = BinderOperationsService(db)
    items, total = service.get_overdue_binders(page=page, page_size=page_size)
    
    enriched = [
        BinderDetailResponse(**service.enrich_binder_with_sla(b, db))
        for b in items
    ]
    
    return BinderListResponseExtended(
        items=enriched,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/due-today", response_model=BinderListResponseExtended)
def list_due_today_binders(
    db: DBSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List binders due today (expected_return_at == today, status != RETURNED)."""
    service = BinderOperationsService(db)
    items, total = service.get_due_today_binders(page=page, page_size=page_size)
    
    enriched = [
        BinderDetailResponse(**service.enrich_binder_with_sla(b, db))
        for b in items
    ]
    
    return BinderListResponseExtended(
        items=enriched,
        page=page,
        page_size=page_size,
        total=total,
    )
