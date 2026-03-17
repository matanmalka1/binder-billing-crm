"""Routes: invoice data entry (add / update / delete / list)."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.users.api.deps import CurrentUser, DBSession
from app.vat_reports.models.vat_enums import InvoiceType
from app.vat_reports.schemas import (
    VatInvoiceCreateRequest,
    VatInvoiceListResponse,
    VatInvoiceResponse,
    VatInvoiceUpdateRequest,
)
from app.vat_reports.services.vat_report_service import VatReportService

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
    """Add an income or expense invoice to a work item."""
    service = VatReportService(db)
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
        rate_type=request.rate_type,
        document_type=request.document_type,
    )
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


@router.patch(
    "/work-items/{item_id}/invoices/{invoice_id}",
    response_model=VatInvoiceResponse,
)
def update_invoice(
    item_id: int,
    invoice_id: int,
    request: VatInvoiceUpdateRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    """Update an existing invoice. Not allowed after filing."""
    service = VatReportService(db)
    invoice = service.update_invoice(
        item_id=item_id,
        invoice_id=invoice_id,
        performed_by=current_user.id,
        net_amount=float(request.net_amount) if request.net_amount is not None else None,
        vat_amount=float(request.vat_amount) if request.vat_amount is not None else None,
        invoice_number=request.invoice_number,
        invoice_date=request.invoice_date,
        counterparty_name=request.counterparty_name,
        expense_category=request.expense_category,
        rate_type=request.rate_type,
        document_type=request.document_type,
    )
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="החשבונית לא נמצאה")
    return invoice


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
    """Delete an invoice from a work item. Not allowed after filing."""
    service = VatReportService(db)
    deleted = service.delete_invoice(
        item_id=item_id,
        invoice_id=invoice_id,
        performed_by=current_user.id,
    )

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="החשבונית לא נמצאה")
