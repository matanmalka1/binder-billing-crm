"""Work item creation and material intake flows."""

import json
from typing import Optional

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.clients.repositories.client_repository import ClientRepository
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.repositories.vat_invoice_repository import VatInvoiceRepository
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.vat_reports.services.constants import ACTION_MATERIAL_RECEIVED


def create_work_item(
    work_item_repo: VatWorkItemRepository,
    client_repo: ClientRepository,
    *,
    client_id: int,
    period: str,
    created_by: int,
    assigned_to: Optional[int] = None,
    mark_pending: bool = False,
    pending_materials_note: Optional[str] = None,
):
    """
    Create a new VAT work item for a client / period.

    Rules:
    - Client must exist.
    - Only one work item per (client_id, period) — duplicate raises AppError.
    - If mark_pending=True the item starts in PENDING_MATERIALS; note is required.
    - Otherwise starts in MATERIAL_RECEIVED.
    """
    client = client_repo.get_by_id(client_id)
    if not client:
        raise NotFoundError(f"Client not found: לקוח {client_id} לא נמצא", "VAT.NOT_FOUND")

    existing = work_item_repo.get_by_client_period(client_id, period)
    if existing:
        raise ConflictError(
            f"already exists: פריט עבודה למע\"מ כבר קיים עבור לקוח {client_id} לתקופה {period}",
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

    item = work_item_repo.create(
        client_id=client_id,
        period=period,
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
        raise NotFoundError(f"not found: פריט עבודה {item_id} למע\"מ לא נמצא", "VAT.NOT_FOUND")

    if item.status != VatWorkItemStatus.PENDING_MATERIALS:
        raise AppError(
            f"Cannot mark materials complete: לא ניתן לסמן חומרים כהושלמו מסטטוס {item.status.value}",
            "VAT.INVALID_TRANSITION",
        )

    from app.vat_reports.services.constants import ACTION_STATUS_CHANGED

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
