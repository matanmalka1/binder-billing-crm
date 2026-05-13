from __future__ import annotations

from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from app.tasks.repositories.task_repository import TaskRepository
from app.utils.time_utils import israel_today
from app.work_queue.schemas.work_queue import (
    LinkedTaskSummary,
    WorkQueueItem,
    WorkQueueSourceSummary,
    WorkQueueSourceType,
    WorkQueueUrgency,
    WorkQueueWarning,
)
from app.work_queue.services.actions import source_actions, task_actions
from app.work_queue.services.billing_items import advance_payment_items, charge_items
from app.work_queue.services.binder_items import binder_items
from app.work_queue.services.common import (
    WorkQueueContext,
    normalize_source_domain,
    source_key,
    urgency,
)
from app.work_queue.services.source_lookup import load_source_states
from app.work_queue.services.task_items import task_item, task_summary
from app.work_queue.services.tax_items import annual_report_items, vat_work_item_items

_FAR_FUTURE = date(9999, 12, 31)
_URGENCY_SORT = {
    WorkQueueUrgency.OVERDUE: 0,
    WorkQueueUrgency.APPROACHING: 1,
    WorkQueueUrgency.IMPORTANT: 2,
    WorkQueueUrgency.UPCOMING: 3,
}
_PRIORITY_SORT = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
_TASK_STATUS_SORT = {"in_progress": 0, "open": 1}


class WorkQueueService:
    def __init__(self, db: Session):
        self.ctx = WorkQueueContext(db, israel_today())

    def list_items(
        self,
        client_record_id: Optional[int] = None,
        business_id: Optional[int] = None,
        exclude_source_types: Optional[List[WorkQueueSourceType]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[WorkQueueItem]:
        excluded = set(exclude_source_types or [])
        system_items: List[WorkQueueItem] = []

        # VAT, annual reports, and advance payments are client-level obligations —
        # business_id does not narrow them; skip entirely when business_id is set.
        if business_id is None:
            if WorkQueueSourceType.VAT_WORK_ITEM not in excluded:
                system_items.extend(vat_work_item_items(self.ctx, client_record_id))
            if WorkQueueSourceType.ANNUAL_REPORT not in excluded:
                system_items.extend(annual_report_items(self.ctx, client_record_id))
            if WorkQueueSourceType.ADVANCE_PAYMENT not in excluded:
                system_items.extend(advance_payment_items(self.ctx, client_record_id))

        if WorkQueueSourceType.CHARGE not in excluded:
            system_items.extend(
                charge_items(self.ctx, client_record_id, business_id)
            )

        # Stale binders are not client-scoped in the current query surface; include
        # when no client/business filter is active.
        if client_record_id is None and business_id is None:
            if WorkQueueSourceType.BINDER not in excluded:
                system_items.extend(binder_items(self.ctx))

        for item in system_items:
            item.available_actions = source_actions(
                item.source_type,
                item.source_id,
            )

        items = self._merge_tasks(
            system_items,
            excluded=excluded,
            client_record_id=client_record_id,
            business_id=business_id,
        )

        items.sort(key=self._sort_key)
        return items[offset : offset + limit]

    def _merge_tasks(
        self,
        system_items: list[WorkQueueItem],
        *,
        excluded: set[WorkQueueSourceType],
        client_record_id: Optional[int],
        business_id: Optional[int],
    ) -> list[WorkQueueItem]:
        if WorkQueueSourceType.TASK in excluded or business_id is not None:
            return system_items

        system_by_key = {
            source_key(item.source_type, item.source_id): item for item in system_items
        }
        tasks = TaskRepository(self.ctx.db).list_open_for_work_queue()
        linked_keys = {
            (source_type, task.source_id)
            for task in tasks
            if task.source_id is not None
            for source_type in [normalize_source_domain(task.source_domain)]
            if source_type is not None
        }
        source_states = load_source_states(self.ctx.db, linked_keys)
        rows = list(system_items)

        for task in tasks:
            source_type = normalize_source_domain(task.source_domain)
            task_source_id = task.source_id
            if source_type is not None and task_source_id is not None:
                key = source_key(source_type, task_source_id)
                source_item = system_by_key.get(key)
                if source_item is not None:
                    self._attach_task(source_item, task_summary(task))
                    continue

            standalone = task_item(self.ctx, task)
            if source_type is not None and task_source_id is not None:
                state = source_states.get((source_type.value, task_source_id))
                if state is not None and client_record_id is not None:
                    if state.client_record_id != client_record_id:
                        continue
                if state is not None:
                    standalone.client_record_id = state.client_record_id
                    standalone.source_summary = WorkQueueSourceSummary(
                        source_type=source_type.value,
                        source_id=task_source_id,
                        label=state.label,
                        route=state.route if not state.is_missing else None,
                    )
                    if state.is_missing or state.is_deleted:
                        standalone.warnings.append(
                            WorkQueueWarning(
                                key="source_missing",
                                label="הפריט המקושר לא נמצא או נמחק",
                                severity="warning",
                            )
                        )
                    elif state.is_final:
                        standalone.warnings.append(
                            WorkQueueWarning(
                                key="source_final",
                                label="הפריט המקושר כבר טופל",
                                severity="info",
                            )
                        )
                else:
                    standalone.warnings.append(
                        WorkQueueWarning(
                            key="source_unknown",
                            label="סוג הקישור של המשימה אינו מוכר",
                            severity="warning",
                        )
                    )
            elif task.source_domain:
                standalone.warnings.append(
                    WorkQueueWarning(
                        key="source_unknown",
                        label="סוג הקישור של המשימה אינו מוכר",
                        severity="warning",
                    )
                )

            if client_record_id is None:
                rows.append(standalone)
            elif standalone.client_record_id == client_record_id:
                rows.append(standalone)

        return rows

    def _attach_task(self, item: WorkQueueItem, task: LinkedTaskSummary) -> None:
        item.linked_tasks.append(task)
        item.linked_tasks_count = len(item.linked_tasks)
        existing_endpoints = {action.endpoint for action in item.available_actions}
        for action in task_actions(task.id, task.status, key_suffix=True):
            if action.endpoint not in existing_endpoints:
                item.available_actions.append(action)
                existing_endpoints.add(action.endpoint)
        if task.due_date is not None:
            task_urgency = urgency(task.due_date, self.ctx.today)
            if _URGENCY_SORT[task_urgency] < _URGENCY_SORT[item.urgency]:
                item.urgency = task_urgency
                item.due_date = task.due_date

    def _sort_key(self, item: WorkQueueItem):
        task_status = None
        priority = None
        if item.source_type == WorkQueueSourceType.TASK and item.metadata:
            task_status = item.metadata.get("status")
            priority = item.metadata.get("priority")
        elif item.linked_tasks:
            task_status = item.linked_tasks[0].status
            priority = item.linked_tasks[0].priority
        return (
            _URGENCY_SORT.get(item.urgency, 99),
            item.due_date if item.due_date is not None else _FAR_FUTURE,
            _TASK_STATUS_SORT.get(str(task_status), 9),
            _PRIORITY_SORT.get(str(priority), 9),
            item.client_name or "",
            item.title,
        )
