from fastapi import APIRouter, Depends, Query

from app.users.api.deps import DBSession, require_role
from app.users.models.user import UserRole
from app.timeline.schemas.timeline import ClientTimelineResponse, TimelineEvent
from app.timeline.services.timeline_service import TimelineService

router = APIRouter(
    prefix="/businesses",
    tags=["timeline"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get("/{business_id}/timeline", response_model=ClientTimelineResponse)
def get_business_timeline(
    business_id: int,
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    """Get unified client timeline."""
    service = TimelineService(db)
    events, total = service.get_business_timeline(
        business_id=business_id,
        page=page,
        page_size=page_size,
    )

    return ClientTimelineResponse(
        business_id=business_id,
        events=[TimelineEvent(**e) for e in events],
        page=page,
        page_size=page_size,
        total=total,
    )
