from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.work_queue.schemas.work_queue import WorkQueueItem, WorkQueueSourceType
from app.work_queue.services.work_queue_service import WorkQueueService

router = APIRouter(prefix="/work-queue", tags=["work-queue"])


@router.get(
    "",
    response_model=List[WorkQueueItem],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def list_work_queue(
    db: DBSession,
    _user: CurrentUser,
    client_record_id: Optional[int] = Query(None),
    business_id: Optional[int] = Query(None),
    exclude_source_types: Optional[List[WorkQueueSourceType]] = Query(None),
):
    return WorkQueueService(db).list_items(
        client_record_id=client_record_id,
        business_id=business_id,
        exclude_source_types=exclude_source_types,
    )
