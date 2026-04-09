"""Advisor review and filing flows."""

import json
from typing import Optional

from app.common.enums import SubmissionMethod
from app.core.exceptions import AppError, NotFoundError
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.vat_reports.services.constants import ACTION_FILED, ACTION_OVERRIDE
from app.vat_reports.services.data_entry_common import assert_transition_allowed


def _validate_amendment(
    work_item_repo: VatWorkItemRepository,
    item,
    amends_item_id: int,
) -> None:
    amended_item = work_item_repo.get_by_id(amends_item_id)
    if amended_item is None:
        raise AppError("פריט מתוקן לא נמצא", code="AMENDED_ITEM_NOT_FOUND", status_code=404)
    if amended_item.client_id != item.client_id:
        raise AppError("פריט מתוקן שייך ללקוח אחר", code="AMENDED_ITEM_WRONG_CLIENT", status_code=400)
    if amended_item.status != VatWorkItemStatus.FILED:
        raise AppError("ניתן לתקן רק פריט שהוגש", code="AMENDED_ITEM_NOT_FILED", status_code=400)

    current_item = amended_item
    while current_item is not None:
        if current_item.id == item.id:
            raise AppError("זוהתה שרשרת תיקונים מעגלית", code="AMENDMENT_CYCLE", status_code=400)
        if current_item.amends_item_id is None:
            break
        current_item = work_item_repo.get_by_id(current_item.amends_item_id)


def file_vat_return(
    work_item_repo: VatWorkItemRepository,
    *,
    item_id: int,
    filed_by: int,
    submission_method: SubmissionMethod,
    override_amount: Optional[float] = None,
    override_justification: Optional[str] = None,
    submission_reference: Optional[str] = None,
    is_amendment: bool = False,
    amends_item_id: Optional[int] = None,
):
    item = work_item_repo.get_by_id_for_update(item_id)
    if not item:
        raise NotFoundError(f"פריט עבודה {item_id} למע\"מ לא נמצא", "VAT.NOT_FOUND")

    assert_transition_allowed(item, VatWorkItemStatus.FILED)

    if amends_item_id is not None:
        _validate_amendment(work_item_repo, item, amends_item_id)

    is_overridden = override_amount is not None

    if is_overridden and override_amount <= 0:
        raise AppError("סכום דריסה חייב להיות חיובי", code="INVALID_OVERRIDE_AMOUNT", status_code=400)

    if is_overridden and not override_justification:
        raise AppError("נדרש נימוק כאשר מחליפים את הסכום", "VAT.JUSTIFICATION_REQUIRED")

    if item.net_vat is None and override_amount is None:
        raise AppError("סכום מע״מ סופי חייב להיות מוגדר", code="MISSING_FINAL_AMOUNT", status_code=400)

    if is_overridden:
        final_amount = override_amount
        work_item_repo.append_audit(
            work_item_id=item_id,
            performed_by=filed_by,
            action=ACTION_OVERRIDE,
            old_value=str(item.net_vat),
            new_value=str(override_amount),
            note=override_justification,
        )
    else:
        final_amount = float(item.net_vat)

    filed_item = work_item_repo.mark_filed(
        item_id=item_id,
        final_vat_amount=final_amount,
        submission_method=submission_method,
        filed_by=filed_by,
        is_overridden=is_overridden,
        override_justification=override_justification if is_overridden else None,
        submission_reference=submission_reference,
        is_amendment=is_amendment,
        amends_item_id=amends_item_id,
        item=item,
    )

    work_item_repo.append_audit(
        work_item_id=item_id,
        performed_by=filed_by,
        action=ACTION_FILED,
        new_value=json.dumps({
            "final_vat_amount": str(final_amount),
            "submission_method": submission_method.value,
            "is_overridden": is_overridden,
        }),
    )

    return filed_item
