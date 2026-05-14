from __future__ import annotations

from typing import Literal

from app.tasks.models.task import TaskStatus
from app.work_queue.schemas.work_queue import WorkQueueAction, WorkQueueSourceType
from app.work_queue.services.common import source_route

HttpMethod = Literal["get", "post", "patch", "put", "delete"]
ActionVariant = Literal["primary", "secondary", "danger"]


def _link(key: str, label: str, route: str, *, primary: bool = False) -> WorkQueueAction:
    return WorkQueueAction(
        key=key,
        label=label,
        type="link",
        route=route,
        variant="primary" if primary else "secondary",
    )


def _mutation(
    key: str,
    label: str,
    endpoint: str,
    *,
    task_id: int | None = None,
    method: HttpMethod = "post",
    confirm_title: str | None = None,
    confirm_message: str | None = None,
    variant: ActionVariant = "secondary",
) -> WorkQueueAction:
    return WorkQueueAction(
        key=key,
        label=label,
        type="mutation",
        endpoint=endpoint,
        method=method,
        task_id=task_id,
        confirm=confirm_title is not None or confirm_message is not None,
        confirm_title=confirm_title,
        confirm_message=confirm_message,
        variant=variant,
    )


def _modal(
    key: str,
    label: str,
    *,
    task_id: int | None = None,
    primary: bool = False,
    variant: ActionVariant | None = None,
) -> WorkQueueAction:
    return WorkQueueAction(
        key=key,
        label=label,
        type="modal",
        task_id=task_id,
        variant=variant or ("primary" if primary else "secondary"),
    )


def source_link_action(source_type: WorkQueueSourceType, source_id: int) -> WorkQueueAction | None:
    route = source_route(source_type, source_id)
    if route is None:
        return None
    labels = {
        WorkQueueSourceType.VAT_WORK_ITEM: 'פתח תיק מע"מ',
        WorkQueueSourceType.ANNUAL_REPORT: "פתח דוח שנתי",
        WorkQueueSourceType.ADVANCE_PAYMENT: "פתח מקדמות",
        WorkQueueSourceType.CHARGE: "פתח חיובים",
        WorkQueueSourceType.BINDER: "פתח קלסרים",
    }
    keys = {
        WorkQueueSourceType.VAT_WORK_ITEM: "open_vat_work_item",
        WorkQueueSourceType.ANNUAL_REPORT: "open_annual_report",
        WorkQueueSourceType.ADVANCE_PAYMENT: "open_advance_payment_context",
        WorkQueueSourceType.CHARGE: "open_charge_context",
        WorkQueueSourceType.BINDER: "open_binder_context",
    }
    key = keys.get(source_type)
    label = labels.get(source_type)
    if key is None or label is None:
        return None
    return _link(key, label, route, primary=True)


def task_actions(
    task_id: int,
    status: str,
    *,
    key_suffix: bool = False,
    include_open: bool = True,
    include_delete: bool = True,
    label_context: str | None = None,
) -> list[WorkQueueAction]:
    actions: list[WorkQueueAction] = []
    suffix = f"_{task_id}" if key_suffix else ""
    label_suffix = f": {label_context}" if label_context else ""
    if include_open:
        actions.append(
            _modal(
                f"continue_task{suffix}",
                f"טפל{label_suffix}",
                task_id=task_id,
                primary=True,
            )
        )
    if status == TaskStatus.OPEN.value:
        actions.append(
            _modal(f"edit_task{suffix}", f"ערוך משימה{label_suffix}", task_id=task_id)
        )
        actions.extend(
            [
                _mutation(
                    f"complete_task{suffix}",
                    f"סמן כהושלמה{label_suffix}",
                    f"/tasks/{task_id}/complete",
                    task_id=task_id,
                    confirm_title="השלמת משימה",
                    confirm_message="האם לסמן את המשימה כהושלמה?",
                    variant="primary",
                ),
                _mutation(
                    f"cancel_task{suffix}",
                    f"בטל משימה{label_suffix}",
                    f"/tasks/{task_id}/cancel",
                    task_id=task_id,
                    confirm_title="ביטול משימה",
                    confirm_message="האם לבטל את המשימה?",
                    variant="danger",
                ),
            ]
        )
    if include_delete:
        actions.append(
            _mutation(
                f"delete_task{suffix}",
                f"מחק משימה{label_suffix}",
                f"/tasks/{task_id}",
                task_id=task_id,
                method="delete",
                confirm_title="מחיקת משימה",
                confirm_message="האם למחוק את המשימה? המחיקה לא תשפיע על מקור המערכת.",
                variant="danger",
            )
        )
    return actions


def create_linked_task_action() -> WorkQueueAction:
    return WorkQueueAction(
        key="create_linked_task",
        label="צור משימה",
        type="modal",
        variant="secondary",
    )


def source_actions(
    source_type: WorkQueueSourceType,
    source_id: int,
) -> list[WorkQueueAction]:
    actions = []
    open_action = source_link_action(source_type, source_id)
    if open_action is not None:
        actions.append(open_action)
    if source_type != WorkQueueSourceType.TASK:
        actions.append(create_linked_task_action())
    return actions


__all__ = [
    "create_linked_task_action",
    "source_actions",
    "source_link_action",
    "task_actions",
]
