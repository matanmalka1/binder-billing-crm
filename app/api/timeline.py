from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, DBSession, require_role
from app.models import UserRole
from app.schemas.timeline import ClientTimelineResponse, TimelineEvent
from app.services.timeline_service import TimelineService

router = APIRouter(
    prefix="/clients",
    tags=["timeline"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get("/{client_id}/timeline", response_model=ClientTimelineResponse)
def get_client_timeline(
    client_id: int,
    db: DBSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Get unified client timeline."""
    service = TimelineService(db)
    events, total = service.get_client_timeline(
        client_id=client_id,
        page=page,
        page_size=page_size,
    )

    return ClientTimelineResponse(
        client_id=client_id,
        events=[TimelineEvent(**e) for e in events],
        page=page,
        page_size=page_size,
        total=total,
    )