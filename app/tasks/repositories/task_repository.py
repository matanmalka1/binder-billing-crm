from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.repositories.base_repository import BaseRepository
from app.tasks.models.task import Task, TaskPriority, TaskStatus


class TaskRepository(BaseRepository[Task]):
    model = Task

    def __init__(self, db: Session):
        super().__init__(db)

    def create(
        self,
        title: str,
        created_by_user_id: Optional[int] = None,
        **kwargs,
    ) -> Task:
        task = Task(title=title, created_by_user_id=created_by_user_id, **kwargs)
        self.db.add(task)
        self.db.flush()
        return task

    def list_active(
        self,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        assigned_to_user_id: Optional[int] = None,
        assigned_role: Optional[str] = None,
        source_domain: Optional[str] = None,
        source_id: Optional[int] = None,
        due_before: Optional[datetime] = None,
        due_after: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ):
        stmt = select(Task).where(Task.deleted_at.is_(None))
        if status is not None:
            stmt = stmt.where(Task.status == status)
        if priority is not None:
            stmt = stmt.where(Task.priority == priority)
        if assigned_to_user_id is not None:
            stmt = stmt.where(Task.assigned_to_user_id == assigned_to_user_id)
        if assigned_role is not None:
            stmt = stmt.where(Task.assigned_role == assigned_role)
        if source_domain is not None:
            stmt = stmt.where(Task.source_domain == source_domain)
        if source_id is not None:
            stmt = stmt.where(Task.source_id == source_id)
        if due_before is not None:
            stmt = stmt.where(Task.due_date <= due_before)
        if due_after is not None:
            stmt = stmt.where(Task.due_date >= due_after)

        count_stmt = select(Task.id).where(Task.deleted_at.is_(None))
        if status is not None:
            count_stmt = count_stmt.where(Task.status == status)
        if priority is not None:
            count_stmt = count_stmt.where(Task.priority == priority)
        if assigned_to_user_id is not None:
            count_stmt = count_stmt.where(Task.assigned_to_user_id == assigned_to_user_id)
        if assigned_role is not None:
            count_stmt = count_stmt.where(Task.assigned_role == assigned_role)
        if source_domain is not None:
            count_stmt = count_stmt.where(Task.source_domain == source_domain)
        if source_id is not None:
            count_stmt = count_stmt.where(Task.source_id == source_id)
        if due_before is not None:
            count_stmt = count_stmt.where(Task.due_date <= due_before)
        if due_after is not None:
            count_stmt = count_stmt.where(Task.due_date >= due_after)

        total = len(self.db.scalars(count_stmt).all())
        stmt = stmt.order_by(Task.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        items = list(self.db.scalars(stmt).all())
        return items, total

    def list_open_for_work_queue(self) -> list[Task]:
        stmt = (
            select(Task)
            .where(
                Task.deleted_at.is_(None),
                Task.status.in_([TaskStatus.OPEN, TaskStatus.IN_PROGRESS]),
            )
        )
        return list(self.db.scalars(stmt).all())
