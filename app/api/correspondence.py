from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUser, DBSession, require_role
from app.models import UserRole
from app.models.correspondence import CorrespondenceType
from app.schemas.correspondence import (
    CorrespondenceCreateRequest,
    CorrespondenceListResponse,
    CorrespondenceResponse,
)
from app.services.correspondence_service import CorrespondenceService

router = APIRouter(
    prefix="/clients",
    tags=["correspondence"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get("/{client_id}/correspondence", response_model=CorrespondenceListResponse)
def list_correspondence(client_id: int, db: DBSession, user: CurrentUser):
    service = CorrespondenceService(db)
    entries = service.list_client_entries(client_id)
    return CorrespondenceListResponse(
        items=[CorrespondenceResponse.model_validate(e) for e in entries]
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
