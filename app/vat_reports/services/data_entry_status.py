"""Status transitions for VAT work items during data entry."""

from app.core.exceptions import AppError, NotFoundError
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.vat_reports.services.constants import ACTION_STATUS_CHANGED
from app.vat_reports.services.data_entry_common import assert_transition_allowed


def mark_ready_for_review(
    work_item_repo: VatWorkItemRepository,
    *,
    item_id: int,
    performed_by: int,
):
    """
    Transition DATA_ENTRY_IN_PROGRESS → READY_FOR_REVIEW.

    Raises:
        AppError: If not in DATA_ENTRY_IN_PROGRESS.
    """
    item = work_item_repo.get_by_id_for_update(item_id)
    if not item:
        raise NotFoundError(f"פריט עבודה {item_id} למע\"מ לא נמצא", "VAT.NOT_FOUND")

    if item.status != VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS:
        raise AppError(
            f"לא ניתן לסמן מוכן לבדיקה מסטטוס {item.status.value}",
            "VAT.INVALID_TRANSITION",
        )

    updated = work_item_repo.update_status(item_id, VatWorkItemStatus.READY_FOR_REVIEW, item=item)

    work_item_repo.append_audit(
        work_item_id=item_id,
        performed_by=performed_by,
        action=ACTION_STATUS_CHANGED,
        old_value=VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS.value,
        new_value=VatWorkItemStatus.READY_FOR_REVIEW.value,
    )

    return updated


def send_back_for_correction(
    work_item_repo: VatWorkItemRepository,
    *,
    item_id: int,
    performed_by: int,
    correction_note: str,
):
    """
    Advisor sends work item back for correction.
    READY_FOR_REVIEW → DATA_ENTRY_IN_PROGRESS.

    Requires a non-empty correction note.
    """
    if not correction_note or not correction_note.strip():
        raise AppError(
            "נדרש טקסט תיקון כאשר מחזירים את הפריט לתיקון",
            "VAT.JUSTIFICATION_REQUIRED",
        )

    item = work_item_repo.get_by_id_for_update(item_id)
    if not item:
        raise NotFoundError(f"פריט עבודה {item_id} למע\"מ לא נמצא", "VAT.NOT_FOUND")

    assert_transition_allowed(item, VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS)

    updated = work_item_repo.update_status(item_id, VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS, item=item)

    work_item_repo.append_audit(
        work_item_id=item_id,
        performed_by=performed_by,
        action=ACTION_STATUS_CHANGED,
        old_value=VatWorkItemStatus.READY_FOR_REVIEW.value,
        new_value=VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS.value,
        note=correction_note,
    )

    return updated
