from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.users.api.deps import DBSession, require_role
from app.users.models.user import UserRole
from app.tasks.models.task import TaskStatus
from app.work_queue.schemas.work_queue import (
    WorkQueueLinkedFilter,
    WorkQueueListResponse,
    WorkQueueScope,
    WorkQueueSourceType,
    WorkQueueSummary,
    WorkQueueUrgency,
)
from app.work_queue.services.work_queue_service import WorkQueueService

router = APIRouter(prefix="/work-queue", tags=["work-queue"])

_LIMIT_MAX = 200
_LIMIT_DEFAULT = 50


class WorkQueueFilterParams:
    def __init__(
        self,
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
        self.client_record_id = client_record_id
        self.business_id = business_id
        self.exclude_source_types = exclude_source_types
        self.include_task_history = include_task_history
        self.search = search
        self.source_type = source_type
        self.urgency = urgency
        self.task_status = task_status
        self.linked = linked
        self.scope = scope


@router.get(
    "/summary",
    response_model=WorkQueueSummary,
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def work_queue_summary(
    db: DBSession,
    filters: WorkQueueFilterParams = Depends(),
):
    return WorkQueueService(db).summary(
        client_record_id=filters.client_record_id,
        business_id=filters.business_id,
        exclude_source_types=filters.exclude_source_types,
        include_task_history=filters.include_task_history,
        search=filters.search,
        source_type=filters.source_type,
        urgency=filters.urgency,
        task_status=filters.task_status,
        linked=filters.linked,
        scope=filters.scope,
    )


@router.get(
    "",
    response_model=WorkQueueListResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def list_work_queue(
    db: DBSession,
    filters: WorkQueueFilterParams = Depends(),
    limit: int = Query(_LIMIT_DEFAULT, ge=1, le=_LIMIT_MAX),
    offset: int = Query(0, ge=0),
):
    return WorkQueueService(db).list_items_with_total(
        client_record_id=filters.client_record_id,
        business_id=filters.business_id,
        exclude_source_types=filters.exclude_source_types,
        include_task_history=filters.include_task_history,
        search=filters.search,
        source_type=filters.source_type,
        urgency=filters.urgency,
        task_status=filters.task_status,
        linked=filters.linked,
        scope=filters.scope,
        limit=limit,
        offset=offset,
    )
