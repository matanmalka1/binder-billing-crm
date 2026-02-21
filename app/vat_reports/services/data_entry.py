"""Data entry flows — add/delete invoices and manage entry status."""

import json
from datetime import datetime
from typing import Optional

from app.vat_reports.models.vat_enums import (
    ExpenseCategory,
    InvoiceType,
    VatWorkItemStatus,
)
from app.vat_reports.repositories.vat_invoice_repository import VatInvoiceRepository
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.vat_reports.services.constants import (
    ACTION_INVOICE_ADDED,
    ACTION_INVOICE_DELETED,
    ACTION_STATUS_CHANGED,
    VALID_TRANSITIONS,
)


def _assert_editable(item) -> None:
    """Raise if the work item is FILED (immutable)."""
    if item.status == VatWorkItemStatus.FILED:
        raise ValueError("Cannot modify a filed VAT work item")


def _assert_transition_allowed(item, target_status: VatWorkItemStatus) -> None:
    """Validate status transition against the central transition table."""
    allowed = VALID_TRANSITIONS.get(item.status, set())
    if target_status not in allowed:
        raise ValueError(
            f"Cannot transition from {item.status.value} to {target_status.value}"
        )


def _recalculate_totals(
    work_item_repo: VatWorkItemRepository,
    invoice_repo: VatInvoiceRepository,
    item_id: int,
) -> None:
    """Recompute output / input VAT totals from stored invoices (single query)."""
    output_vat, input_vat = invoice_repo.sum_vat_both_types(item_id)
    work_item_repo.update_vat_totals(item_id, output_vat, input_vat)


def add_invoice(
    work_item_repo: VatWorkItemRepository,
    invoice_repo: VatInvoiceRepository,
    *,
    item_id: int,
    created_by: int,
    invoice_type: InvoiceType,
    invoice_number: str,
    invoice_date: datetime,
    counterparty_name: str,
    net_amount: float,
    vat_amount: float,
    counterparty_id: Optional[str] = None,
    expense_category: Optional[ExpenseCategory] = None,
):
    """
    Add an invoice to a work item.

    Rules:
    - Work item must exist and not be FILED.
    - Work item must be in DATA_ENTRY_IN_PROGRESS (auto-transitions from
      MATERIAL_RECEIVED on first invoice).
    - VAT amount must be >= 0.
    - Net amount must be > 0.
    - Invoice number must be unique per (work_item, type).
    - EXPENSE invoices require expense_category.
    """
    item = work_item_repo.get_by_id(item_id)
    if not item:
        raise ValueError(f"VAT work item {item_id} not found")

    _assert_editable(item)

    if vat_amount < 0:
        raise ValueError("VAT amount cannot be negative")

    if net_amount <= 0:
        raise ValueError("Net amount must be positive")

    if invoice_type == InvoiceType.EXPENSE and not expense_category:
        raise ValueError("expense_category is required for expense invoices")

    # Duplicate invoice number check
    existing = invoice_repo.get_by_number(item_id, invoice_type, invoice_number)
    if existing:
        raise ValueError(
            f"Invoice number '{invoice_number}' already exists for this period and type"
        )

    original_status = item.status

    # Auto-transition MATERIAL_RECEIVED → DATA_ENTRY_IN_PROGRESS on first invoice
    if original_status == VatWorkItemStatus.MATERIAL_RECEIVED:
        work_item_repo.update_status(item_id, VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS)
        work_item_repo.append_audit(
            work_item_id=item_id,
            performed_by=created_by,
            action=ACTION_STATUS_CHANGED,
            old_value=VatWorkItemStatus.MATERIAL_RECEIVED.value,
            new_value=VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS.value,
            note="Auto-transitioned on first invoice entry",
        )
    elif original_status not in (
        VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS,
        VatWorkItemStatus.READY_FOR_REVIEW,  # allow advisor to add during review
    ):
        raise ValueError(
            f"Cannot add invoices to work item in status {original_status.value}"
        )

    invoice = invoice_repo.create(
        work_item_id=item_id,
        created_by=created_by,
        invoice_type=invoice_type,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        counterparty_name=counterparty_name,
        counterparty_id=counterparty_id,
        net_amount=net_amount,
        vat_amount=vat_amount,
        expense_category=expense_category,
    )

    _recalculate_totals(work_item_repo, invoice_repo, item_id)

    work_item_repo.append_audit(
        work_item_id=item_id,
        performed_by=created_by,
        action=ACTION_INVOICE_ADDED,
        new_value=json.dumps(
            {
                "invoice_id": invoice.id,
                "type": invoice_type.value,
                "number": invoice_number,
                "vat_amount": str(vat_amount),
            }
        ),
    )

    return invoice


def delete_invoice(
    work_item_repo: VatWorkItemRepository,
    invoice_repo: VatInvoiceRepository,
    *,
    item_id: int,
    invoice_id: int,
    performed_by: int,
):
    """
    Delete an invoice from a work item.

    Rules:
    - Work item must not be FILED.
    - Invoice must belong to this work item.
    """
    item = work_item_repo.get_by_id(item_id)
    if not item:
        raise ValueError(f"VAT work item {item_id} not found")

    _assert_editable(item)

    invoice = invoice_repo.get_by_id(invoice_id)
    if not invoice or invoice.work_item_id != item_id:
        raise ValueError(f"Invoice {invoice_id} not found on work item {item_id}")

    snapshot = json.dumps(
        {
            "invoice_id": invoice.id,
            "type": invoice.invoice_type.value,
            "number": invoice.invoice_number,
            "vat_amount": str(invoice.vat_amount),
        }
    )

    deleted = invoice_repo.delete(invoice_id)
    if deleted:
        _recalculate_totals(work_item_repo, invoice_repo, item_id)
        work_item_repo.append_audit(
            work_item_id=item_id,
            performed_by=performed_by,
            action=ACTION_INVOICE_DELETED,
            old_value=snapshot,
        )

    return deleted


def mark_ready_for_review(
    work_item_repo: VatWorkItemRepository,
    *,
    item_id: int,
    performed_by: int,
):
    """
    Transition DATA_ENTRY_IN_PROGRESS → READY_FOR_REVIEW.

    Raises:
        ValueError: If not in DATA_ENTRY_IN_PROGRESS.
    """
    item = work_item_repo.get_by_id(item_id)
    if not item:
        raise ValueError(f"VAT work item {item_id} not found")

    if item.status != VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS:
        raise ValueError(
            f"Cannot mark ready for review from status {item.status.value}"
        )

    updated = work_item_repo.update_status(item_id, VatWorkItemStatus.READY_FOR_REVIEW)

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
        raise ValueError("correction_note is required when sending back for correction")

    item = work_item_repo.get_by_id(item_id)
    if not item:
        raise ValueError(f"VAT work item {item_id} not found")

    _assert_transition_allowed(item, VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS)

    updated = work_item_repo.update_status(
        item_id, VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS
    )

    work_item_repo.append_audit(
        work_item_id=item_id,
        performed_by=performed_by,
        action=ACTION_STATUS_CHANGED,
        old_value=VatWorkItemStatus.READY_FOR_REVIEW.value,
        new_value=VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS.value,
        note=correction_note,
    )

    return updated
