"""Shared helpers for VAT work item data-entry flows."""

import json
from decimal import Decimal
from typing import Optional

from app.core.exceptions import AppError
from app.common.enums import EntityType
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.models.vat_enums import DocumentType, InvoiceType
from app.vat_reports.repositories.vat_invoice_repository import VatInvoiceRepository
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.vat_reports.services.constants import (
    CATEGORY_DEDUCTION_RATES,
    EXCEPTIONAL_INVOICE_THRESHOLD,
    OSEK_PATUR_CEILING_ILS,
    OSEK_PATUR_CEILING_WARNING_RATE,
    VALID_TRANSITIONS,
)
from app.vat_reports.services.messages import (
    VAT_EXPENSE_CATEGORY_REQUIRED,
    VAT_FILED_ITEM_IMMUTABLE,
    VAT_INVALID_TRANSITION,
    VAT_NEGATIVE_AMOUNT,
    VAT_NET_AMOUNT_POSITIVE_REQUIRED,
    VAT_OSEK_PATUR_CEILING_EXCEEDED,
    VAT_SUPPLIER_ID_REQUIRED,
)


def assert_editable(item) -> None:
    """Raise if the work item is FILED (immutable)."""
    if item.status == VatWorkItemStatus.FILED:
        raise AppError(VAT_FILED_ITEM_IMMUTABLE, "VAT.FILED_IMMUTABLE")


def assert_transition_allowed(item, target_status: VatWorkItemStatus) -> None:
    """Validate status transition against the central transition table."""
    allowed = VALID_TRANSITIONS.get(item.status, set())
    if target_status not in allowed:
        raise AppError(
            VAT_INVALID_TRANSITION.format(
                current_status=item.status.value,
                target_status=target_status.value,
            ),
            "VAT.INVALID_TRANSITION",
        )


def recalculate_totals(
    work_item_repo: VatWorkItemRepository,
    invoice_repo: VatInvoiceRepository,
    item_id: int,
) -> tuple[Decimal, Decimal]:
    """Recompute output / input VAT totals from stored invoices (single query)."""
    output_vat, input_vat = invoice_repo.sum_vat_both_types(item_id)
    output_net, input_net = invoice_repo.sum_net_both_types(item_id)
    work_item_repo.update_vat_totals(item_id, output_vat, input_vat, output_net, input_net)
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


def resolve_invoice_derived_fields(
    invoice_type,
    expense_category,
    document_type,
    counterparty_id: Optional[str],
    net_amount: float,
    vat_amount: float,
) -> dict:
    """Validate amounts/category rules and return derived fields: deduction_rate, is_exceptional."""
    if vat_amount < 0:
        raise AppError(VAT_NEGATIVE_AMOUNT, "VAT.NEGATIVE_VAT")
    if net_amount <= 0:
        raise AppError(VAT_NET_AMOUNT_POSITIVE_REQUIRED, "VAT.NET_NOT_POSITIVE")
    if invoice_type == InvoiceType.EXPENSE and not expense_category:
        raise AppError(
            VAT_EXPENSE_CATEGORY_REQUIRED,
            "VAT.EXPENSE_CATEGORY_REQUIRED",
        )
    if (
        invoice_type == InvoiceType.EXPENSE
        and document_type == DocumentType.TAX_INVOICE
        and not counterparty_id
    ):
        raise AppError(
            VAT_SUPPLIER_ID_REQUIRED,
            "VAT.COUNTERPARTY_ID_REQUIRED",
        )

    deduction_rate = Decimal("1.0000")
    if invoice_type == InvoiceType.EXPENSE and expense_category:
        deduction_rate = CATEGORY_DEDUCTION_RATES.get(
            expense_category.value, Decimal("0.0000")
        )
    is_exceptional = Decimal(str(net_amount)) > EXCEPTIONAL_INVOICE_THRESHOLD
    return {"deduction_rate": deduction_rate, "is_exceptional": is_exceptional}


def check_osek_patur_ceiling(
    client,
    invoice_repo: VatInvoiceRepository,
    client_id: int,
    period: str,
    new_net_amount: float,
) -> bool:
    """Raise AppError if adding this income invoice would exceed the OSEK PATUR ceiling.
    Returns True if the post-add turnover crosses the 80% warning threshold (non-blocking).
    Only enforced for OSEK_PATUR clients (EntityType.OSEK_PATUR).
    """
    is_osek_patur = (
        getattr(client, "entity_type", None) == EntityType.OSEK_PATUR
    )
    if not is_osek_patur:
        return False
    year = int(period[:4])
    current_total = Decimal(str(invoice_repo.sum_income_net_by_client_year(client_id, year)))
    new_total = current_total + Decimal(str(new_net_amount))
    if new_total > OSEK_PATUR_CEILING_ILS:
        raise AppError(
            VAT_OSEK_PATUR_CEILING_EXCEEDED.format(
                new_total=float(new_total),
                ceiling=float(OSEK_PATUR_CEILING_ILS),
            ),
            "VAT.OSEK_PATUR_CEILING_EXCEEDED",
        )
    return new_total >= OSEK_PATUR_CEILING_ILS * OSEK_PATUR_CEILING_WARNING_RATE
