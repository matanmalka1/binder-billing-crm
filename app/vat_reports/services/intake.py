"""Work item creation and material intake flows."""

import json
from typing import Optional
from types import SimpleNamespace

from app.common.enums import VatType
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.repositories.legal_entity_repository import LegalEntityRepository
from app.clients.guards.client_record_guards import assert_client_record_is_active
from app.clients.enums import ClientStatus
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.vat_reports.services.constants import ACTION_MATERIAL_RECEIVED, ACTION_STATUS_CHANGED, ACTION_WORK_ITEM_CREATED_PENDING
from app.vat_reports.services.messages import (
    VAT_CLIENT_CLOSED_CREATE_ITEM,
    VAT_CLIENT_EXEMPT,
    VAT_CLIENT_FROZEN_CREATE_ITEM,
    VAT_CLIENT_NOT_FOUND,
    VAT_INVALID_BIMONTHLY_PERIOD,
    VAT_ITEM_NOT_FOUND,
    VAT_MATERIALS_COMPLETE_INVALID_STATUS,
    VAT_PENDING_MATERIALS_NOTE_REQUIRED,
    VAT_WORK_ITEM_CONFLICT,
)
from app.vat_reports.services.vat_type_resolver import resolve_effective_vat_type


def _validate_period_for_vat_type(period: str, vat_type: VatType) -> None:
    """Raise AppError if period doesn't match the client's reporting frequency."""
    if vat_type == VatType.EXEMPT:
        raise AppError(
            VAT_CLIENT_EXEMPT,
            "VAT.CLIENT_EXEMPT",
        )
    if vat_type == VatType.BIMONTHLY:
        month = int(period.split("-")[1])
        if month % 2 == 0:
            raise AppError(
                VAT_INVALID_BIMONTHLY_PERIOD.format(period=period),
                "VAT.INVALID_PERIOD_FOR_FREQUENCY",
            )


def create_work_item(
    work_item_repo: VatWorkItemRepository,
    db,
    *,
    client_record_id: Optional[int] = None,
    client_id: Optional[int] = None,
    period: str,
    created_by: int,
    assigned_to: Optional[int] = None,
    mark_pending: bool = False,
    pending_materials_note: Optional[str] = None,
):
    """
    Create a new VAT work item for a client / period.

    Rules:
    - Client must exist and not be CLOSED or FROZEN.
    - Only one work item per (client_record_id, period) — duplicate raises ConflictError.
    - Period must match the client's reporting frequency.
    - If mark_pending=True the item starts in PENDING_MATERIALS; note is required.
    - Otherwise starts in MATERIAL_RECEIVED.
    """
    legacy_client_repo = db if hasattr(db, "db") and hasattr(db, "get_by_id") else None
    db_session = legacy_client_repo.db if legacy_client_repo is not None else db
    if client_record_id is None:
        client_record_id = client_id
    if client_record_id is None:
        raise NotFoundError(VAT_CLIENT_NOT_FOUND.format(client_record_id=""), "VAT.NOT_FOUND")

    client_record = ClientRecordRepository(db_session).get_by_id(client_record_id)
    if client_record:
        assert_client_record_is_active(client_record)
        client_record_id = client_record.id
        legal_entity = LegalEntityRepository(db_session).get_by_id(client_record.legal_entity_id)
        if not legal_entity:
            raise NotFoundError(
                VAT_CLIENT_NOT_FOUND.format(client_record_id=client_record_id),
                "VAT.NOT_FOUND",
            )
    elif legacy_client_repo is not None:
        legacy_client = legacy_client_repo.get_by_id(client_record_id)
        if not legacy_client:
            raise NotFoundError(VAT_CLIENT_NOT_FOUND.format(client_record_id=client_record_id), "VAT.NOT_FOUND")
        client_record = SimpleNamespace(id=client_record_id, status=getattr(legacy_client, "status", ClientStatus.ACTIVE))
        legal_entity = legacy_client
    else:
        raise NotFoundError(VAT_CLIENT_NOT_FOUND.format(client_record_id=client_record_id), "VAT.NOT_FOUND")
    if client_record.status == ClientStatus.CLOSED:
        raise AppError(VAT_CLIENT_CLOSED_CREATE_ITEM, "VAT.CLIENT_CLOSED")
    if client_record.status == ClientStatus.FROZEN:
        raise AppError(VAT_CLIENT_FROZEN_CREATE_ITEM, "VAT.CLIENT_FROZEN")
    effective_vat_type = resolve_effective_vat_type(legal_entity)
    _validate_period_for_vat_type(period, effective_vat_type)

    # WARNING: This check only filters for non-deleted items (deleted_at IS NULL).
    # If we ever allow soft-deleting FILED items, this guard must be updated to
    # also block creation when a FILED item exists for the same period, even if deleted.
    existing = work_item_repo.get_by_client_record_period(client_record_id, period)
    if existing:
        raise ConflictError(
            VAT_WORK_ITEM_CONFLICT.format(client_record_id=client_record_id, period=period),
            "VAT.CONFLICT",
        )

    if mark_pending:
        if not pending_materials_note:
            raise AppError(
                VAT_PENDING_MATERIALS_NOTE_REQUIRED,
                "VAT.PENDING_NOTE_REQUIRED",
            )
        status = VatWorkItemStatus.PENDING_MATERIALS
    else:
        status = VatWorkItemStatus.MATERIAL_RECEIVED

    item = work_item_repo.create(
        client_record_id=client_record_id,
        period=period,
        period_type=effective_vat_type,
        created_by=created_by,
        status=status,
        pending_materials_note=pending_materials_note,
        assigned_to=assigned_to,
    )

    action = ACTION_WORK_ITEM_CREATED_PENDING if mark_pending else ACTION_MATERIAL_RECEIVED
    work_item_repo.append_audit(
        work_item_id=item.id,
        performed_by=created_by,
        action=action,
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
    item = work_item_repo.get_by_id_for_update(item_id)
    if not item:
        raise NotFoundError(VAT_ITEM_NOT_FOUND.format(item_id=item_id), "VAT.NOT_FOUND")

    if item.status != VatWorkItemStatus.PENDING_MATERIALS:
        raise AppError(
            VAT_MATERIALS_COMPLETE_INVALID_STATUS.format(status=item.status.value),
            "VAT.INVALID_TRANSITION",
        )

    old_status = item.status.value
    updated = work_item_repo.update_status(
        item_id,
        VatWorkItemStatus.MATERIAL_RECEIVED,
        item=item,
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
