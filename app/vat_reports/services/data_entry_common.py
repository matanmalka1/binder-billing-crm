"""Shared helpers for VAT work item data-entry flows."""

import json
from typing import Tuple

from app.core.exceptions import AppError
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.repositories.vat_invoice_repository import VatInvoiceRepository
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.vat_reports.services.constants import VALID_TRANSITIONS


def assert_editable(item) -> None:
    """Raise if the work item is FILED (immutable)."""
    if item.status == VatWorkItemStatus.FILED:
        raise AppError("filed: לא ניתן לערוך פריט עבודה שלמע\"מ שכבר הוגש", "VAT.FILED_IMMUTABLE")


def assert_transition_allowed(item, target_status: VatWorkItemStatus) -> None:
    """Validate status transition against the central transition table."""
    allowed = VALID_TRANSITIONS.get(item.status, set())
    if target_status not in allowed:
        raise AppError(
            f"לא ניתן לעבור מ-{item.status.value} ל-{target_status.value}",
            "VAT.INVALID_TRANSITION",
        )


def recalculate_totals(
    work_item_repo: VatWorkItemRepository,
    invoice_repo: VatInvoiceRepository,
    item_id: int,
) -> Tuple[float, float]:
    """Recompute output / input VAT totals from stored invoices (single query)."""
    output_vat, input_vat = invoice_repo.sum_vat_both_types(item_id)
    work_item_repo.update_vat_totals(item_id, output_vat, input_vat)
    return output_vat, input_vat


def audit_invoice_snapshot(invoice) -> str:
    return json.dumps(
        {
            "invoice_id": invoice.id,
            "type": invoice.invoice_type.value,
            "number": invoice.invoice_number,
            "vat_amount": str(invoice.vat_amount),
        }
    )
