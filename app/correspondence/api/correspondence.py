from fastapi import APIRouter, Depends, HTTPException, Query, status

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

router = APIRouter(
    prefix="/clients",
    tags=["correspondence"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get("/{client_id}/correspondence", response_model=CorrespondenceListResponse)
def list_correspondence(
    client_id: int,
    db: DBSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    service = CorrespondenceService(db)
    entries, total = service.list_client_entries(client_id, page=page, page_size=page_size)
    return CorrespondenceListResponse(
        items=[CorrespondenceResponse.model_validate(e) for e in entries],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post(
    "/{client_id}/correspondence",
    response_model=CorrespondenceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_correspondence(
    client_id: int,
    request: CorrespondenceCreateRequest,
    db: DBSession,
    user: CurrentUser,
):
    try:
        corr_type = CorrespondenceType(request.correspondence_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid correspondence_type: {request.correspondence_type}",
        )
    service = CorrespondenceService(db)
    try:
        entry = service.add_entry(
            client_id=client_id,
            correspondence_type=corr_type,
            subject=request.subject,
            occurred_at=request.occurred_at,
            created_by=user.id,
            contact_id=request.contact_id,
            notes=request.notes,
        )
        return CorrespondenceResponse.model_validate(entry)
    except ValueError as e:
        detail = str(e)
        if "not found" in detail:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


@router.patch(
    "/{client_id}/correspondence/{correspondence_id}",
    response_model=CorrespondenceResponse,
)
def update_correspondence(
    client_id: int,
    correspondence_id: int,
    request: CorrespondenceUpdateRequest,
    db: DBSession,
    user: CurrentUser,
):
    update_data = request.model_dump(exclude_unset=True)
    if "correspondence_type" in update_data:
        try:
            update_data["correspondence_type"] = CorrespondenceType(
                update_data["correspondence_type"]
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid correspondence_type: {update_data['correspondence_type']}",
            )
    service = CorrespondenceService(db)
    try:
        entry = service.update_entry(correspondence_id, client_id, **update_data)
        return CorrespondenceResponse.model_validate(entry)
    except ValueError as e:
        detail = str(e)
        if "not found" in detail:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


@router.delete(
    "/{client_id}/correspondence/{correspondence_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def delete_correspondence(
    client_id: int,
    correspondence_id: int,
    db: DBSession,
    user: CurrentUser,
):
    service = CorrespondenceService(db)
    try:
        service.delete_entry(correspondence_id, client_id, actor_id=user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
