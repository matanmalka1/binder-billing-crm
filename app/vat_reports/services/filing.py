"""Advisor review and filing flows."""

import json
from typing import Optional

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.vat_reports.models.vat_enums import FilingMethod, VatWorkItemStatus
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.vat_reports.services.constants import ACTION_FILED, ACTION_OVERRIDE


def file_vat_return(
    work_item_repo: VatWorkItemRepository,
    *,
    item_id: int,
    filed_by: int,
    filing_method: FilingMethod,
    override_amount: Optional[float] = None,
    override_justification: Optional[str] = None,
    submission_reference: Optional[str] = None,
    is_amendment: bool = False,
    amends_item_id: Optional[int] = None,
):
    """
    Advisor confirms and files the VAT return.

    Rules:
    - Work item must be in READY_FOR_REVIEW.
    - Filing method must be provided.
    - If override_amount is provided, override_justification is mandatory.
    - If no override, final_vat_amount = system-calculated net_vat.
    - Status becomes FILED (immutable — no further edits allowed).

    Raises:
        AppError: Any rule violation.
    """
    item = work_item_repo.get_by_id(item_id)
    if not item:
        raise NotFoundError(f"not found: פריט עבודה {item_id} למע\"מ לא נמצא", "VAT.NOT_FOUND")

    if item.status != VatWorkItemStatus.READY_FOR_REVIEW:
        raise AppError(
            f"Cannot file VAT return from status {item.status.value}. "
            "Work item must be READY_FOR_REVIEW.",
            "VAT.INVALID_TRANSITION",
        )

    is_overridden = override_amount is not None

    if is_overridden and not override_justification:
        raise AppError("justification: נדרש נימוק כאשר מחליפים את הסכום למע\"מ", "VAT.JUSTIFICATION_REQUIRED")

    if is_overridden:
        final_amount = override_amount
        # Log the override before filing
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
        filing_method=filing_method,
        filed_by=filed_by,
        is_overridden=is_overridden,
        override_justification=override_justification if is_overridden else None,
        submission_reference=submission_reference,
        is_amendment=is_amendment,
        amends_item_id=amends_item_id,
    )

    work_item_repo.append_audit(
        work_item_id=item_id,
        performed_by=filed_by,
        action=ACTION_FILED,
        new_value=json.dumps(
            {
                "final_vat_amount": str(final_amount),
                "filing_method": filing_method.value,
                "is_overridden": is_overridden,
            }
        ),
    )

    return filed_item
