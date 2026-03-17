"""Invoice add flow for VAT work items."""

import json
from datetime import datetime
from typing import Optional
from uuid import uuid4

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.vat_reports.models.vat_enums import ExpenseCategory, InvoiceType, VatWorkItemStatus
from app.vat_reports.repositories.vat_invoice_repository import VatInvoiceRepository
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.vat_reports.services.constants import (
    ACTION_INVOICE_ADDED,
    ACTION_STATUS_CHANGED,
    CATEGORY_LABELS_SERVER,
)
from app.vat_reports.services.data_entry_common import audit_invoice_snapshot, assert_editable, recalculate_totals


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
):
    """
    Add an invoice to a work item.

    Rules:
    - Work item must exist and not be FILED.
    - Work item must be in DATA_ENTRY_IN_PROGRESS (auto-transitions from MATERIAL_RECEIVED on first invoice).
    - VAT amount must be >= 0.
    - Net amount must be > 0.
    - Invoice number must be unique per (work_item, type).
    - EXPENSE invoices require expense_category.
    """
    item = work_item_repo.get_by_id(item_id)
    if not item:
        raise NotFoundError(f"not found: פריט עבודה {item_id} למע\"מ לא נמצא", "VAT.NOT_FOUND")

    assert_editable(item)

    if vat_amount < 0:
        raise AppError("negative: הסכום של המע\"מ לא יכול להיות שלילי", "VAT.NEGATIVE_VAT")
    if net_amount <= 0:
        raise AppError("positive: הסכום נטו חייב להיות חיובי", "VAT.NET_NOT_POSITIVE")
    if invoice_type == InvoiceType.EXPENSE and not expense_category:
        raise AppError(
            "expense_category: חובה לציין קטגוריית הוצאה עבור חשבוניות הוצאה",
            "VAT.EXPENSE_CATEGORY_REQUIRED",
        )

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
    )

    recalculate_totals(work_item_repo, invoice_repo, item_id)

    work_item_repo.append_audit(
        work_item_id=item_id,
        performed_by=created_by,
        action=ACTION_INVOICE_ADDED,
        new_value=json.dumps(
            {"invoice_id": invoice.id, "type": invoice_type.value, "number": invoice_number, "vat_amount": str(vat_amount)}
        ),
    )

    return invoice
