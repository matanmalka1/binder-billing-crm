from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.users.api.deps import DBSession, require_role
from app.users.models.user import UserRole
from app.tasks.models.task import TaskStatus
from app.work_queue.schemas.work_queue import (
    WorkQueueItem,
    WorkQueueLinkedFilter,
    WorkQueueScope,
    WorkQueueSourceType,
    WorkQueueSummary,
    WorkQueueUrgency,
)
from app.work_queue.services.work_queue_service import WorkQueueService

router = APIRouter(prefix="/work-queue", tags=["work-queue"])

_LIMIT_MAX = 200
_LIMIT_DEFAULT = 50


@router.get(
    "/summary",
    response_model=WorkQueueSummary,
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def work_queue_summary(
    db: DBSession,
    client_record_id: Optional[int] = Query(None),
    business_id: Optional[int] = Query(None),
    exclude_source_types: Optional[List[WorkQueueSourceType]] = Query(None),
    include_task_history: bool = Query(False),
    search: Optional[str] = Query(None),
    source_type: Optional[WorkQueueSourceType] = Query(None),
    urgency: Optional[WorkQueueUrgency] = Query(None),
    task_status: Optional[TaskStatus] = Query(None),
    linked: Optional[WorkQueueLinkedFilter] = Query(None),
    scope: Optional[WorkQueueScope] = Query(None),
):
    return WorkQueueService(db).summary(
        client_record_id=client_record_id,
        business_id=business_id,
        exclude_source_types=exclude_source_types,
        include_task_history=include_task_history,
        search=search,
        source_type=source_type,
        urgency=urgency,
        task_status=task_status,
        linked=linked,
        scope=scope,
    )


@router.get(
    "",
    response_model=List[WorkQueueItem],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def list_work_queue(
    db: DBSession,
    client_record_id: Optional[int] = Query(None),
    business_id: Optional[int] = Query(None),
    exclude_source_types: Optional[List[WorkQueueSourceType]] = Query(None),
    include_task_history: bool = Query(False),
    search: Optional[str] = Query(None),
    source_type: Optional[WorkQueueSourceType] = Query(None),
    urgency: Optional[WorkQueueUrgency] = Query(None),
    task_status: Optional[TaskStatus] = Query(None),
    linked: Optional[WorkQueueLinkedFilter] = Query(None),
    scope: Optional[WorkQueueScope] = Query(None),
    limit: int = Query(_LIMIT_DEFAULT, ge=1, le=_LIMIT_MAX),
    offset: int = Query(0, ge=0),
):
    return WorkQueueService(db).list_items(
        client_record_id=client_record_id,
        business_id=business_id,
        exclude_source_types=exclude_source_types,
        include_task_history=include_task_history,
        search=search,
        source_type=source_type,
        urgency=urgency,
        task_status=task_status,
        linked=linked,
        scope=scope,
        limit=limit,
        offset=offset,
    )
