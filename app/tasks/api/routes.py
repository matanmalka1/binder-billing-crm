from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.tasks.schemas.task import DeadlineTask, TaskType, UnifiedItem
from app.tasks.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get(
    "",
    response_model=List[DeadlineTask],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def list_tasks(
    db: DBSession,
    _user: CurrentUser,
    client_record_id: Optional[int] = Query(None),
    business_id: Optional[int] = Query(None),
    exclude_source_types: Optional[List[TaskType]] = Query(None),
):
    return TaskService(db).get_tasks(
        client_record_id=client_record_id,
        business_id=business_id,
        exclude_source_types=exclude_source_types,
    )


@router.get(
    "/unified",
    response_model=List[UnifiedItem],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def list_unified(
    db: DBSession,
    _user: CurrentUser,
    client_record_id: Optional[int] = Query(None),
    business_id: Optional[int] = Query(None),
    exclude_source_types: Optional[List[TaskType]] = Query(None),
    include_reminders: bool = Query(True),
):
    return TaskService(db).get_unified(
        client_record_id=client_record_id,
        business_id=business_id,
        exclude_source_types=exclude_source_types,
        include_reminders=include_reminders,
    )
