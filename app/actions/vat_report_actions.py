from __future__ import annotations

from app.actions.action_helpers import (
    ActionContract,
    _generate_action_id,
    _value,
    build_action,
    build_confirm,
)
from app.users.models.user import UserRole
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.models.vat_work_item import VatWorkItem


def _is_advisor(user_role: UserRole | str | None) -> bool:
    return user_role in (UserRole.ADVISOR, UserRole.ADVISOR.value)


def get_vat_work_item_actions(
    item: VatWorkItem,
    *,
    user_role: UserRole | str | None = None,
) -> list[ActionContract]:
    """Return executable actions for a VAT work item."""
    status = _value(item.status)
    actions: list[ActionContract] = []

    if status == VatWorkItemStatus.PENDING_MATERIALS.value:
        actions.append(
            build_action(
                key="materials_complete",
                label="אישור קבלת חומרים",
                method="post",
                endpoint=f"/vat/work-items/{item.id}/materials-complete",
                action_id=_generate_action_id("vat_work_item", item.id, "materials_complete"),
            )
        )

    if status in {
        VatWorkItemStatus.MATERIAL_RECEIVED.value,
        VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS.value,
        VatWorkItemStatus.READY_FOR_REVIEW.value,
    }:
        actions.append(
            build_action(
                key="add_invoice",
                label="הוספת חשבונית",
                method="post",
                endpoint=f"/vat/work-items/{item.id}/invoices",
                action_id=_generate_action_id("vat_work_item", item.id, "add_invoice"),
            )
        )

    if status == VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS.value:
        actions.append(
            build_action(
                key="ready_for_review",
                label="שלח לבדיקה",
                method="post",
                endpoint=f"/vat/work-items/{item.id}/ready-for-review",
                action_id=_generate_action_id("vat_work_item", item.id, "ready_for_review"),
            )
        )

    if _is_advisor(user_role) and status == VatWorkItemStatus.READY_FOR_REVIEW.value:
        actions.extend([
            build_action(
                key="file_vat_return",
                label='הגש מע"מ',
                method="post",
                endpoint=f"/vat/work-items/{item.id}/file",
                action_id=_generate_action_id("vat_work_item", item.id, "file_vat_return"),
            ),
            build_action(
                key="send_back",
                label="החזר לתיקון",
                method="post",
                endpoint=f"/vat/work-items/{item.id}/send-back",
                action_id=_generate_action_id("vat_work_item", item.id, "send_back"),
                confirm=build_confirm(
                    "החזרה לתיקון",
                    "יש לציין הערה לפני החזרת התיק לתיקון.",
                ),
            ),
        ])

    return actions


__all__ = ["get_vat_work_item_actions"]
