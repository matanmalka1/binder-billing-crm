"""Routes: invoice data entry (add / delete / list)."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.users.api.deps import CurrentUser, DBSession
from app.vat_reports.models.vat_enums import InvoiceType
from app.vat_reports.schemas import (
    SendBackForCorrectionRequest,
    VatInvoiceCreateRequest,
    VatInvoiceListResponse,
    VatInvoiceResponse,
    VatWorkItemResponse,
)
from app.vat_reports.services.service import VatReportService

router = APIRouter(prefix="/vat", tags=["vat-reports"])


@router.post(
    "/work-items/{item_id}/invoices",
    response_model=VatInvoiceResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_invoice(
    item_id: int,
    request: VatInvoiceCreateRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Add an income or expense invoice to a work item.

    Accessible by: secretary, advisor.
    """
    service = VatReportService(db)
    try:
        invoice = service.add_invoice(
            item_id=item_id,
            created_by=current_user.id,
            invoice_type=request.invoice_type,
            invoice_number=request.invoice_number,
            invoice_date=request.invoice_date,
            counterparty_name=request.counterparty_name,
            net_amount=float(request.net_amount),
            vat_amount=float(request.vat_amount),
            counterparty_id=request.counterparty_id,
            expense_category=request.expense_category,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return invoice


@router.get(
    "/work-items/{item_id}/invoices",
    response_model=VatInvoiceListResponse,
)
def list_invoices(
    item_id: int,
    db: DBSession,
    current_user: CurrentUser,
    invoice_type: Optional[InvoiceType] = Query(default=None),
):
    """List invoices for a work item, optionally filtered by type."""
    service = VatReportService(db)
    items = service.list_invoices(item_id=item_id, invoice_type=invoice_type)
    return VatInvoiceListResponse(items=items)


@router.delete(
    "/work-items/{item_id}/invoices/{invoice_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_invoice(
    item_id: int,
    invoice_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Delete an invoice from a work item.

    Not allowed after filing.
    """
    service = VatReportService(db)
    try:
        deleted = service.delete_invoice(
            item_id=item_id,
            invoice_id=invoice_id,
            performed_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")


@router.post(
    "/work-items/{item_id}/ready-for-review",
    response_model=VatWorkItemResponse,
)
def mark_ready_for_review(
    item_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Mark data entry complete: DATA_ENTRY_IN_PROGRESS → READY_FOR_REVIEW.

    Accessible by: secretary, advisor.
    """
    service = VatReportService(db)
    try:
        item = service.mark_ready_for_review(
            item_id=item_id,
            performed_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return item


@router.post(
    "/work-items/{item_id}/send-back",
    response_model=VatWorkItemResponse,
)
def send_back_for_correction(
    item_id: int,
    request: SendBackForCorrectionRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Advisor sends work item back for correction.
    READY_FOR_REVIEW → DATA_ENTRY_IN_PROGRESS.

    Advisor only.
    """
    from app.users.api.deps import require_role
    from app.users.models.user import UserRole

    if current_user.role not in (UserRole.ADVISOR,):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only advisors can send work items back for correction",
        )

    service = VatReportService(db)
    try:
        item = service.send_back_for_correction(
            item_id=item_id,
            performed_by=current_user.id,
            correction_note=request.correction_note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return item
