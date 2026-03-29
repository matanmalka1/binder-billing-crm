"""Work item creation and material intake flows."""

import json
from typing import Optional

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.businesses.models.business_tax_profile import VatType
from app.businesses.repositories.business_repository import BusinessRepository
from app.businesses.repositories.business_tax_profile_repository import BusinessTaxProfileRepository
from app.businesses.services.business_guards import assert_business_allows_create
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.vat_reports.services.constants import ACTION_MATERIAL_RECEIVED, ACTION_STATUS_CHANGED


def _validate_period_for_vat_type(period: str, vat_type: VatType) -> None:
    """Raise AppError if period doesn't match the business's reporting frequency."""
    if vat_type == VatType.EXEMPT:
        raise AppError(
            "עסק זה פטור ממע\"מ ולא ניתן לפתוח עבורו דוח",
            "VAT.CLIENT_EXEMPT",
        )
    if vat_type == VatType.BIMONTHLY:
        month = int(period.split("-")[1])
        if month % 2 == 0:
            raise AppError(
                f"עסק זה מדווח דו-חודשי — התקופה {period} אינה תקפה (חודשים זוגיים אסורים)",
                "VAT.INVALID_PERIOD_FOR_FREQUENCY",
            )


def create_work_item(
    work_item_repo: VatWorkItemRepository,
    business_repo: BusinessRepository,
    *,
    business_id: int,
    period: str,
    created_by: int,
    tax_profile_repo: Optional[BusinessTaxProfileRepository] = None,
    assigned_to: Optional[int] = None,
    mark_pending: bool = False,
    pending_materials_note: Optional[str] = None,
):
    """
    Create a new VAT work item for a business / period.

    Rules:
    - Business must exist.
    - Only one work item per (business_id, period) — duplicate raises ConflictError.
    - If business has a vat_type, the period must match the reporting frequency.
    - If mark_pending=True the item starts in PENDING_MATERIALS; note is required.
    - Otherwise starts in MATERIAL_RECEIVED.
    """
    business = business_repo.get_by_id(business_id)
    if not business:
        raise NotFoundError(f"עסק {business_id} לא נמצא", "VAT.NOT_FOUND")

    assert_business_allows_create(business)

    profile = None
    if tax_profile_repo is not None:
        profile = tax_profile_repo.get_by_business_id(business_id)
        if profile and profile.vat_type:
            _validate_period_for_vat_type(period, profile.vat_type)

    existing = work_item_repo.get_by_business_period(business_id, period)
    if existing:
        raise ConflictError(
            f"פריט עבודה למע\"מ כבר קיים עבור עסק {business_id} לתקופה {period}",
            "VAT.CONFLICT",
        )

    if mark_pending:
        if not pending_materials_note:
            raise AppError(
                "pending_materials_note: נדרש תיאור החומרים כאשר הפריט מסומן כמצב המתנה",
                "VAT.PENDING_NOTE_REQUIRED",
            )
        status = VatWorkItemStatus.PENDING_MATERIALS
    else:
        status = VatWorkItemStatus.MATERIAL_RECEIVED

    period_type = profile.vat_type if (profile and profile.vat_type) else VatType.MONTHLY

    item = work_item_repo.create(
        business_id=business_id,
        period=period,
        period_type=period_type,
        created_by=created_by,
        status=status,
        pending_materials_note=pending_materials_note,
        assigned_to=assigned_to,
    )

    work_item_repo.append_audit(
        work_item_id=item.id,
        performed_by=created_by,
        action=ACTION_MATERIAL_RECEIVED,
        new_value=json.dumps({"status": status.value, "period": period}),
    )

    return item


def mark_materials_complete(
    work_item_repo: VatWorkItemRepository,
    *,
    item_id: int,
    performed_by: int,
):
    """
    Transition PENDING_MATERIALS → MATERIAL_RECEIVED once all documents arrive.

    Raises:
        AppError: If item not found or not in PENDING_MATERIALS.
    """
    item = work_item_repo.get_by_id(item_id)
    if not item:
        raise NotFoundError(f"פריט עבודה {item_id} למע\"מ לא נמצא", "VAT.NOT_FOUND")

    if item.status != VatWorkItemStatus.PENDING_MATERIALS:
        raise AppError(
            f"לא ניתן לסמן חומרים כהושלמו מסטטוס {item.status.value}",
            "VAT.INVALID_TRANSITION",
        )

    old_status = item.status.value
    updated = work_item_repo.update_status(
        item_id,
        VatWorkItemStatus.MATERIAL_RECEIVED,
        pending_materials_note=None,
    )

    work_item_repo.append_audit(
        work_item_id=item_id,
        performed_by=performed_by,
        action=ACTION_STATUS_CHANGED,
        old_value=old_status,
        new_value=VatWorkItemStatus.MATERIAL_RECEIVED.value,
    )

    return updated
