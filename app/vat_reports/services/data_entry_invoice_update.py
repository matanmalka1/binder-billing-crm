"""Invoice update flow for VAT work items."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from app.core.exceptions import ConflictError, NotFoundError
from app.businesses.repositories.business_repository import BusinessRepository
from app.clients.services.client_lookup import assert_business_not_closed
from app.vat_reports.models.vat_enums import DocumentType, ExpenseCategory, VatRateType
from app.vat_reports.repositories.vat_invoice_repository import VatInvoiceRepository
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.vat_reports.services.constants import (
    ACTION_INVOICE_UPDATED,
    CATEGORY_DEDUCTION_RATES,
    EXCEPTIONAL_INVOICE_THRESHOLD,
)
from app.vat_reports.services.data_entry_common import (
    audit_invoice_snapshot,
    assert_editable,
    recalculate_totals,
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
    expense_category: Optional[ExpenseCategory] = None,
    rate_type: Optional[VatRateType] = None,
    document_type: Optional[DocumentType] = None,
):
    """Update an existing invoice. Work item must not be FILED."""
    item = work_item_repo.get_by_id(item_id)
    if not item:
        raise NotFoundError(f"פריט עבודה {item_id} למע\"מ לא נמצא", "VAT.NOT_FOUND")

    assert_editable(item)

    business = BusinessRepository(work_item_repo.db).get_by_id(item.business_id)
    if business:
        assert_business_not_closed(business)

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

    update_fields: dict = {
        "net_amount": net_amount,
        "vat_amount": vat_amount,
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "counterparty_name": counterparty_name,
        "expense_category": expense_category,
        "rate_type": rate_type,
        "document_type": document_type,
    }
    if expense_category is not None:
        update_fields["deduction_rate"] = float(
            CATEGORY_DEDUCTION_RATES.get(expense_category.value, Decimal("0.0000"))
        )
    effective_net = net_amount if net_amount is not None else float(invoice.net_amount)
    update_fields["is_exceptional"] = Decimal(str(effective_net)) > EXCEPTIONAL_INVOICE_THRESHOLD

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