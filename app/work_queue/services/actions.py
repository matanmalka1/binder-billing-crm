from __future__ import annotations

from app.tasks.models.task import TaskStatus
from app.work_queue.schemas.work_queue import WorkQueueAction, WorkQueueSourceType
from app.work_queue.services.common import source_route


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
    confirm_title: str | None = None,
    confirm_message: str | None = None,
    variant: str = "secondary",
) -> WorkQueueAction:
    return WorkQueueAction(
        key=key,
        label=label,
        type="mutation",
        endpoint=endpoint,
        method="post",
        confirm=confirm_title is not None or confirm_message is not None,
        confirm_title=confirm_title,
        confirm_message=confirm_message,
        variant=variant,  # type: ignore[arg-type]
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
    task_id: int, status: str, *, key_suffix: bool = False
) -> list[WorkQueueAction]:
    actions: list[WorkQueueAction] = []
    suffix = f"_{task_id}" if key_suffix else ""
    if status == TaskStatus.OPEN.value:
        actions.append(
            _mutation(
                f"start_task{suffix}",
                "התחל משימה",
                f"/tasks/{task_id}/start",
                variant="primary",
            )
        )
    if status in {TaskStatus.OPEN.value, TaskStatus.IN_PROGRESS.value}:
        actions.extend(
            [
                _mutation(
                    f"complete_task{suffix}",
                    "סמן כהושלמה",
                    f"/tasks/{task_id}/complete",
                    confirm_title="השלמת משימה",
                    confirm_message="האם לסמן את המשימה כהושלמה?",
                    variant="primary" if status == TaskStatus.IN_PROGRESS.value else "secondary",
                ),
                _mutation(
                    f"cancel_task{suffix}",
                    "בטל משימה",
                    f"/tasks/{task_id}/cancel",
                    confirm_title="ביטול משימה",
                    confirm_message="האם לבטל את המשימה?",
                    variant="danger",
                ),
            ]
        )
    return actions


def source_actions(
    source_type: WorkQueueSourceType,
    source_id: int,
) -> list[WorkQueueAction]:
    actions = []
    open_action = source_link_action(source_type, source_id)
    if open_action is not None:
        actions.append(open_action)
    return actions


__all__ = ["source_actions", "source_link_action", "task_actions"]
