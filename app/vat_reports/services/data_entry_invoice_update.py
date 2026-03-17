"""Invoice update flow for VAT work items."""

from datetime import datetime
from typing import Optional

from app.core.exceptions import ConflictError, NotFoundError
from app.vat_reports.models.vat_enums import ExpenseCategory
from app.vat_reports.repositories.vat_invoice_repository import VatInvoiceRepository
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.vat_reports.services.constants import ACTION_INVOICE_UPDATED
from app.vat_reports.services.data_entry_common import audit_invoice_snapshot, assert_editable, recalculate_totals


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
    expense_category: Optional[ExpenseCategory] = None,
):
    """Update an existing invoice. Work item must not be FILED."""
    item = work_item_repo.get_by_id(item_id)
    if not item:
        raise NotFoundError(f"פריט עבודה {item_id} למע\"מ לא נמצא", "VAT.NOT_FOUND")

    assert_editable(item)

    invoice = invoice_repo.get_by_id(invoice_id)
    if not invoice or invoice.work_item_id != item_id:
        raise NotFoundError(
            f"החשבונית {invoice_id} לא נמצאה בפריט עבודה {item_id}",
            "VAT.NOT_FOUND",
        )

    if invoice_number and invoice_number != invoice.invoice_number:
        existing = invoice_repo.get_by_number(item_id, invoice.invoice_type, invoice_number)
        if existing:
            raise ConflictError(
                f"already exists: מספר חשבונית '{invoice_number}' כבר קיים לתקופה ולסוג הזה",
                "VAT.CONFLICT",
            )

    snapshot_before = audit_invoice_snapshot(invoice)

    updated = invoice_repo.update(
        invoice_id,
        net_amount=net_amount,
        vat_amount=vat_amount,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        counterparty_name=counterparty_name,
        expense_category=expense_category,
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
