from __future__ import annotations

from typing import List

from app.tasks.repositories.task_repository import TaskRepository
from app.work_queue.schemas.work_queue import (
    WorkQueueItem,
    WorkQueueSourceType,
    WorkQueueUrgency,
)
from app.work_queue.services.common import WorkQueueContext, urgency


def task_items(ctx: WorkQueueContext) -> List[WorkQueueItem]:
    repo = TaskRepository(ctx.db)
    tasks = repo.list_open_for_work_queue()
    items: List[WorkQueueItem] = []
    for task in tasks:
        due = task.due_date.date() if task.due_date is not None else None
        item_urgency = urgency(due, ctx.today) if due is not None else WorkQueueUrgency.UPCOMING
        items.append(
            WorkQueueItem(
                source_type=WorkQueueSourceType.TASK,
                source_id=task.id,
                label=task.title,
                due_date=due,
                urgency=item_urgency,
                client_record_id=None,
                client_name=None,
                business_id=None,
                payload={
                    "status": task.status.value,
                    "priority": task.priority.value,
                    "description": task.description,
                    "assigned_to_user_id": task.assigned_to_user_id,
                    "assigned_role": task.assigned_role,
                    "action_key": task.action_key,
                    "action_payload": task.action_payload,
                    "source_domain": task.source_domain,
                    "source_id": task.source_id,
                },
            )
        )
    return items
