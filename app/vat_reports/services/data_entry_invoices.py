"""Invoice add flow for VAT work items."""

import json
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.businesses.repositories.business_repository import BusinessRepository
from app.businesses.services.business_guards import assert_business_not_closed
from app.vat_reports.models.vat_enums import (
    DocumentType,
    ExpenseCategory,
    InvoiceType,
    VatRateType,
    VatWorkItemStatus,
)
from app.vat_reports.repositories.vat_invoice_repository import VatInvoiceRepository
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.vat_reports.services.constants import (
    ACTION_INVOICE_ADDED,
    ACTION_STATUS_CHANGED,
    CATEGORY_LABELS_SERVER,
)
from app.vat_reports.services.data_entry_common import (
    audit_invoice_snapshot,
    assert_editable,
    check_osek_patur_ceiling,
    recalculate_totals,
    resolve_invoice_derived_fields,
)


def add_invoice(
    work_item_repo: VatWorkItemRepository,
    invoice_repo: VatInvoiceRepository,
    *,
    item_id: int,
    created_by: int,
    invoice_type: InvoiceType,
    invoice_number: Optional[str],
    invoice_date: Optional[datetime],
    counterparty_name: Optional[str],
    net_amount: float,
    vat_amount: float,
    counterparty_id: Optional[str] = None,
    expense_category: Optional[ExpenseCategory] = None,
    rate_type: VatRateType = VatRateType.STANDARD,
    document_type: Optional[DocumentType] = None,
):
    """Add an invoice to a work item. Validation delegated to resolve_invoice_derived_fields."""
    item = work_item_repo.get_by_id(item_id)
    if not item:
        raise NotFoundError(f"not found: פריט עבודה {item_id} למע\"מ לא נמצא", "VAT.NOT_FOUND")

    assert_editable(item)

    business = BusinessRepository(work_item_repo.db).get_by_id(item.business_id)
    if business:
        assert_business_not_closed(business)

    derived = resolve_invoice_derived_fields(
        invoice_type, expense_category, document_type, counterparty_id, net_amount, vat_amount
    )
    deduction_rate = derived["deduction_rate"]
    is_exceptional = derived["is_exceptional"]

    if invoice_type == InvoiceType.INCOME and business:
        check_osek_patur_ceiling(business, invoice_repo, item.business_id, item.period, net_amount)

    # Auto-fill optional fields when not provided by caller
    if not invoice_number:
        invoice_number = f"{item.period}-{invoice_type.value}-{uuid4().hex[:8]}"
    if not invoice_date:
        invoice_date = datetime.strptime(f"{item.period}-01", "%Y-%m-%d")
    if not counterparty_name:
        if invoice_type == InvoiceType.INCOME:
            counterparty_name = "הכנסות"
        else:
            counterparty_name = CATEGORY_LABELS_SERVER.get(
                expense_category.value if expense_category else "", "לא ידוע"
            )

    existing = invoice_repo.get_by_number(item_id, invoice_type, invoice_number)
    if existing:
        raise ConflictError(
            f"already exists: מספר חשבונית '{invoice_number}' כבר קיים לתקופה ולסוג הזה",
            "VAT.CONFLICT",
        )

    original_status = item.status

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
        VatWorkItemStatus.READY_FOR_REVIEW,
    ):
        raise AppError(
            f"לא ניתן להוסיף חשבוניות לפריט עבודה במצב {original_status.value}",
            "VAT.INVALID_STATUS",
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
        rate_type=rate_type,
        deduction_rate=float(deduction_rate),
        document_type=document_type,
        is_exceptional=is_exceptional,
    )

    recalculate_totals(work_item_repo, invoice_repo, item_id)

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