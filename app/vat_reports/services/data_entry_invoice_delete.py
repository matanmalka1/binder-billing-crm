"""Invoice delete flow for VAT work items."""

from app.core.exceptions import NotFoundError
from app.vat_reports.repositories.vat_invoice_repository import VatInvoiceRepository
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.vat_reports.services.constants import ACTION_INVOICE_DELETED
from app.vat_reports.services.data_entry_common import audit_invoice_snapshot, assert_editable, recalculate_totals
from app.vat_reports.services.messages import VAT_INVOICE_NOT_FOUND_IN_WORK_ITEM, VAT_ITEM_NOT_FOUND


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
        raise NotFoundError(VAT_ITEM_NOT_FOUND.format(item_id=item_id), "VAT.NOT_FOUND")

    assert_editable(item)

    invoice = invoice_repo.get_by_id(invoice_id)
    if not invoice or invoice.work_item_id != item_id:
        raise NotFoundError(
            VAT_INVOICE_NOT_FOUND_IN_WORK_ITEM.format(invoice_id=invoice_id, item_id=item_id),
            "VAT.NOT_FOUND",
        )

    snapshot = audit_invoice_snapshot(invoice)

    deleted = invoice_repo.delete(invoice_id)
    if deleted:
        recalculate_totals(work_item_repo, invoice_repo, item_id)
        work_item_repo.append_audit(
            work_item_id=item_id,
            performed_by=performed_by,
            action=ACTION_INVOICE_DELETED,
            old_value=snapshot,
        )

    return deleted
