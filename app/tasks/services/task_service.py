from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.common.services.base_service import BaseService
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.tasks.models.task import Task, TaskPriority, TaskStatus
from app.tasks.repositories.task_repository import TaskRepository
from app.tasks.schemas.task import TaskCreateRequest, TaskUpdateRequest
from app.utils.time_utils import utcnow
from app.work_queue.services.common import normalize_source_domain
from app.work_queue.services.source_lookup import load_source_states

_TERMINAL = {TaskStatus.DONE, TaskStatus.CANCELED}

_NOT_FOUND = "TASK.NOT_FOUND"
_CONFLICT = "TASK.CONFLICT"
_INVALID_SOURCE = "TASK.INVALID_SOURCE"


class TaskService(BaseService):
    def __init__(self, db: Session):
        super().__init__(db)
        self.repo = TaskRepository(db)

    def create(
        self, data: TaskCreateRequest, created_by_user_id: Optional[int]
    ) -> Task:
        self._validate_source(data.source_domain, data.source_id)
        with self.transaction():
            return self.repo.create(
                title=data.title,
                created_by_user_id=created_by_user_id,
                description=data.description,
                priority=data.priority,
                due_date=data.due_date,
                assigned_to_user_id=data.assigned_to_user_id,
                assigned_role=data.assigned_role,
                source_domain=data.source_domain,
                source_id=data.source_id,
                action_key=data.action_key,
                action_payload=data.action_payload,
            )

    def get(self, task_id: int) -> Task:
        task = self.repo.get_by_id(task_id)
        if not task or task.deleted_at is not None:
            raise NotFoundError(f"משימה {task_id} לא נמצאה", _NOT_FOUND)
        return task

    def list(
        self,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        assigned_to_user_id: Optional[int] = None,
        assigned_role: Optional[str] = None,
        source_domain: Optional[str] = None,
        source_id: Optional[int] = None,
        due_before=None,
        due_after=None,
        page: int = 1,
        page_size: int = 20,
    ):
        return self.repo.list_active(
            status=status,
            priority=priority,
            assigned_to_user_id=assigned_to_user_id,
            assigned_role=assigned_role,
            source_domain=source_domain,
            source_id=source_id,
            due_before=due_before,
            due_after=due_after,
            page=page,
            page_size=page_size,
        )

    def update(self, task_id: int, data: TaskUpdateRequest) -> Task:
        task = self._get_active(task_id)
        if task.status in _TERMINAL:
            raise ConflictError("לא ניתן לערוך משימה שהושלמה או בוטלה", _CONFLICT)
        updates = data.model_dump(exclude_unset=True)
        with self.transaction():
            for field, value in updates.items():
                setattr(task, field, value)
            task.updated_at = utcnow()
        return task

    def complete(self, task_id: int, completed_by_user_id: Optional[int]) -> Task:
        task = self._get_active(task_id)
        if task.status == TaskStatus.CANCELED:
            raise ConflictError("לא ניתן להשלים משימה שבוטלה", _CONFLICT)
        if task.status == TaskStatus.DONE:
            raise ConflictError("משימה כבר הושלמה", _CONFLICT)
        with self.transaction():
            task.status = TaskStatus.DONE
            task.completed_at = utcnow()
            task.completed_by_user_id = completed_by_user_id
            task.updated_at = utcnow()
        return task

    def cancel(self, task_id: int) -> Task:
        task = self._get_active(task_id)
        if task.status == TaskStatus.DONE:
            raise ConflictError("לא ניתן לבטל משימה שהושלמה", _CONFLICT)
        if task.status == TaskStatus.CANCELED:
            raise ConflictError("משימה כבר בוטלה", _CONFLICT)
        with self.transaction():
            task.status = TaskStatus.CANCELED
            task.canceled_at = utcnow()
            task.updated_at = utcnow()
        return task

    def delete(self, task_id: int) -> None:
        task = self._get_active(task_id)
        with self.transaction():
            task.deleted_at = utcnow()
            task.updated_at = utcnow()

    def _get_active(self, task_id: int) -> Task:
        task = self.repo.get_by_id(task_id)
        if not task or task.deleted_at is not None:
            raise NotFoundError(f"משימה {task_id} לא נמצאה", _NOT_FOUND)
        return task

    def _validate_source(
        self, source_domain: Optional[str], source_id: Optional[int]
    ) -> None:
        if source_domain is None and source_id is None:
            return
        if not source_domain or source_id is None:
            raise AppError(
                "קישור מקור למשימה חייב לכלול סוג מקור ומזהה מקור",
                _INVALID_SOURCE,
            )
        source_type = normalize_source_domain(source_domain)
        if source_type is None:
            raise AppError("סוג המקור של המשימה אינו נתמך", _INVALID_SOURCE)
        state = load_source_states(self.db, [(source_type, source_id)]).get(
            (source_type.value, source_id)
        )
        if state is None or state.is_missing or state.is_deleted:
            raise NotFoundError("הפריט המקושר למשימה לא נמצא", _NOT_FOUND)
