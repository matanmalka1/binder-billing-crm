"""Invoice update flow for VAT work items."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.vat_reports.models.vat_enums import (
    CounterpartyIdType,
    DocumentType,
    ExpenseCategory,
    VatRateType,
)
from app.vat_reports.repositories.vat_invoice_repository import VatInvoiceRepository
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from tax_rules import get_financial, get_vat_deduction_rate
from app.vat_reports.services.constants import ACTION_INVOICE_UPDATED
from app.vat_reports.services.data_entry_common import (
    audit_invoice_snapshot,
    assert_editable,
    recalculate_totals,
)
from app.vat_reports.services.messages import (
    VAT_INVOICE_NOT_FOUND_IN_WORK_ITEM,
    VAT_INVOICE_NUMBER_CONFLICT,
    VAT_ITEM_NOT_FOUND,
    VAT_NEGATIVE_AMOUNT,
    VAT_NET_AMOUNT_POSITIVE_REQUIRED,
)


def update_invoice(
    work_item_repo: VatWorkItemRepository,
    invoice_repo: VatInvoiceRepository,
    *,
    item_id: int,
    invoice_id: int,
    performed_by: int,
    net_amount: Optional[float] = None,
    vat_amount: Optional[float] = None,
    invoice_number: Optional[str] = None,
    invoice_date: Optional[datetime] = None,
    counterparty_name: Optional[str] = None,
    counterparty_id: Optional[str] = None,
    counterparty_id_type: Optional[CounterpartyIdType] = None,
    expense_category: Optional[ExpenseCategory] = None,
    rate_type: Optional[VatRateType] = None,
    document_type: Optional[DocumentType] = None,
    business_activity_id: Optional[int] = None,
):
    """Update an existing invoice. Work item must not be FILED."""
    item = work_item_repo.get_by_id(item_id)
    if not item:
        raise NotFoundError(VAT_ITEM_NOT_FOUND.format(item_id=item_id), "VAT.NOT_FOUND")

    assert_editable(item)

    invoice = invoice_repo.get_by_id(invoice_id)
    if not invoice or invoice.work_item_id != item_id:
        raise NotFoundError(
            VAT_INVOICE_NOT_FOUND_IN_WORK_ITEM.format(invoice_id=invoice_id, item_id=item_id),
            "VAT.NOT_FOUND",
        )

    if invoice_number and invoice_number != invoice.invoice_number:
        existing = invoice_repo.get_by_number(item_id, invoice.invoice_type, invoice_number)
        if existing:
            raise ConflictError(
                VAT_INVOICE_NUMBER_CONFLICT.format(invoice_number=invoice_number),
                "VAT.CONFLICT",
            )

    if net_amount is not None and net_amount <= 0:
        raise AppError(VAT_NET_AMOUNT_POSITIVE_REQUIRED, code="INVALID_NET_AMOUNT", status_code=400)
    if vat_amount is not None and vat_amount < 0:
        raise AppError(VAT_NEGATIVE_AMOUNT, code="INVALID_VAT_AMOUNT", status_code=400)

    snapshot_before = audit_invoice_snapshot(invoice)

    update_fields: dict = {
        "net_amount": net_amount,
        "vat_amount": vat_amount,
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "counterparty_name": counterparty_name,
        "counterparty_id": counterparty_id,
        "counterparty_id_type": counterparty_id_type,
        "expense_category": expense_category,
        "rate_type": rate_type,
        "document_type": document_type,
        "business_activity_id": business_activity_id,
    }
    if expense_category is not None:
        update_fields["deduction_rate"] = get_vat_deduction_rate(expense_category.value)
    effective_net = net_amount if net_amount is not None else float(invoice.net_amount)
    _threshold = Decimal(str(get_financial(2026, "exceptional_invoice_threshold_ils").value))
    update_fields["is_exceptional"] = Decimal(str(effective_net)) > _threshold

    updated = invoice_repo.update(
        invoice_id,
        **{k: v for k, v in update_fields.items() if v is not None or k == "is_exceptional"},
    )

    recalculate_totals(work_item_repo, invoice_repo, item_id)

    work_item_repo.append_audit(
        work_item_id=item_id,
        performed_by=performed_by,
        action=ACTION_INVOICE_UPDATED,
        old_value=snapshot_before,
        new_value=audit_invoice_snapshot(updated),
    )

    return updated
