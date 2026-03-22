from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.correspondence.models.correspondence import CorrespondenceType
from app.correspondence.schemas.correspondence import (
    CorrespondenceCreateRequest,
    CorrespondenceListResponse,
    CorrespondenceResponse,
    CorrespondenceUpdateRequest,
)
from app.correspondence.services.correspondence_service import CorrespondenceService

_DEFAULT_PAGE_SIZE = 20
_MAX_PAGE_SIZE = 100

router = APIRouter(
    prefix="/businesses",
    tags=["correspondence"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get("/{business_id}/correspondence", response_model=CorrespondenceListResponse)
def list_correspondence(
    business_id: int,
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(_DEFAULT_PAGE_SIZE, ge=1, le=_MAX_PAGE_SIZE),
    correspondence_type: Optional[CorrespondenceType] = Query(None),
    contact_id: Optional[int] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    sort_dir: Literal["asc", "desc"] = Query("desc"),
):
    service = CorrespondenceService(db)
    entries, total = service.list_business_entries(
        business_id,
        page=page,
        page_size=page_size,
        correspondence_type=correspondence_type,
        contact_id=contact_id,
        from_date=from_date,
        to_date=to_date,
        sort_dir=sort_dir,
    )
    return CorrespondenceListResponse.build(
        items=[CorrespondenceResponse.model_validate(e) for e in entries],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get(
    "/{business_id}/correspondence/{correspondence_id}",
    response_model=CorrespondenceResponse,
)
def get_correspondence(
    business_id: int,
    correspondence_id: int,
    db: DBSession,
):
    service = CorrespondenceService(db)
    entry = service.get_entry(correspondence_id, business_id)
    return CorrespondenceResponse.model_validate(entry)


@router.post(
    "/{business_id}/correspondence",
    response_model=CorrespondenceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_correspondence(
    business_id: int,
    request: CorrespondenceCreateRequest,
    db: DBSession,
    user: CurrentUser,
):
    service = CorrespondenceService(db)
    entry = service.add_entry(
        business_id=business_id,
        correspondence_type=request.correspondence_type,
        subject=request.subject,
        occurred_at=request.occurred_at,
        created_by=user.id,
        contact_id=request.contact_id,
        notes=request.notes,
    )
    return CorrespondenceResponse.model_validate(entry)


@router.patch(
    "/{business_id}/correspondence/{correspondence_id}",
    response_model=CorrespondenceResponse,
)
def update_correspondence(
    business_id: int,
    correspondence_id: int,
    request: CorrespondenceUpdateRequest,
    db: DBSession,
    user: CurrentUser,
):
    update_data = request.model_dump(exclude_unset=True)
    service = CorrespondenceService(db)
    entry = service.update_entry(correspondence_id, business_id, **update_data)
    return CorrespondenceResponse.model_validate(entry)


@router.delete(
    "/{business_id}/correspondence/{correspondence_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def delete_correspondence(
    business_id: int,
    correspondence_id: int,
    db: DBSession,
    user: CurrentUser,
):
    service = CorrespondenceService(db)
    service.delete_entry(correspondence_id, business_id, actor_id=user.id)
