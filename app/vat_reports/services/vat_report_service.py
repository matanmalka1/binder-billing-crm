"""
VatReportService — thin façade delegating to focused sub-modules.

Follows the same façade pattern used by ReminderService and SignatureRequestService
throughout this codebase.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.clients.repositories.client_repository import ClientRepository
from app.vat_reports.repositories.vat_invoice_repository import VatInvoiceRepository
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.vat_reports.services import data_entry, filing, intake, queries


class VatReportService:
    """Orchestrates the VAT reporting lifecycle.

    Note: This is an intentional façade that simply forwards to the underlying
    intake/data-entry/filing/query modules. Keeping the boundary allows future
    orchestration (cross-cutting validation, metrics, permissions) without
    touching callers that already depend on this service.
    """

    def __init__(self, db: Session):
        self.db = db
        self.work_item_repo = VatWorkItemRepository(db)
        self.invoice_repo = VatInvoiceRepository(db)
        self.client_repo = ClientRepository(db)

    # ── Intake ───────────────────────────────────────────────────────────────

    def create_work_item(self, **kwargs):
        return intake.create_work_item(
            self.work_item_repo, self.client_repo, **kwargs
        )

    def mark_materials_complete(self, **kwargs):
        return intake.mark_materials_complete(self.work_item_repo, **kwargs)

    # ── Data entry ───────────────────────────────────────────────────────────

    def add_invoice(self, **kwargs):
        return data_entry.add_invoice(
            self.work_item_repo, self.invoice_repo, **kwargs
        )

    def delete_invoice(self, **kwargs):
        return data_entry.delete_invoice(
            self.work_item_repo, self.invoice_repo, **kwargs
        )

    def mark_ready_for_review(self, **kwargs):
        return data_entry.mark_ready_for_review(self.work_item_repo, **kwargs)

    def send_back_for_correction(self, **kwargs):
        return data_entry.send_back_for_correction(self.work_item_repo, **kwargs)

    # ── Filing ───────────────────────────────────────────────────────────────

    def file_vat_return(self, **kwargs):
        return filing.file_vat_return(self.work_item_repo, **kwargs)

    # ── Queries ──────────────────────────────────────────────────────────────

    def get_work_item(self, item_id: int):
        return queries.get_work_item(self.work_item_repo, item_id)

    def list_client_work_items(self, client_id: int):
        return queries.list_client_work_items(self.work_item_repo, client_id)

    def list_work_items_by_status(self, **kwargs):
        return queries.list_work_items_by_status(self.work_item_repo, **kwargs)

    def list_all_work_items(self, **kwargs):
        return queries.list_all_work_items(self.work_item_repo, **kwargs)

    def list_invoices(self, **kwargs):
        return queries.list_invoices(self.invoice_repo, **kwargs)

    def get_audit_trail(self, item_id: int):
        return queries.get_audit_trail(self.work_item_repo, item_id)
