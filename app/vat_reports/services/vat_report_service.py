"""
VatReportService — thin façade delegating to focused sub-modules.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.businesses.repositories.business_repository import BusinessRepository
from app.clients.repositories.client_repository import ClientRepository
from app.vat_reports.repositories.vat_invoice_repository import VatInvoiceRepository
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.vat_reports.services import data_entry, filing, intake, period_options, vat_report_queries
from app.vat_reports.services import vat_report_enrichment
from app.users.repositories.user_repository import UserRepository


class VatReportService:
    """Orchestrates the VAT reporting lifecycle."""

    def __init__(self, db: Session):
        self.db = db
        self.work_item_repo = VatWorkItemRepository(db)
        self.invoice_repo = VatInvoiceRepository(db)
        self.business_repo = BusinessRepository(db)
        self.client_repo = ClientRepository(db)
        self.user_repo = UserRepository(db)

    # ── Intake ───────────────────────────────────────────────────────────────

    def create_work_item(self, **kwargs):
        return intake.create_work_item(
            self.work_item_repo, self.client_repo,
            **kwargs,
        )

    def mark_materials_complete(self, **kwargs):
        return intake.mark_materials_complete(self.work_item_repo, **kwargs)

    def get_period_options(self, **kwargs):
        return period_options.get_period_options(
            self.work_item_repo,
            self.client_repo,
            **kwargs,
        )

    # ── Data entry ───────────────────────────────────────────────────────────

    def add_invoice(self, **kwargs):
        return data_entry.add_invoice(self.work_item_repo, self.invoice_repo, self.client_repo, **kwargs)

    def delete_invoice(self, **kwargs):
        return data_entry.delete_invoice(self.work_item_repo, self.invoice_repo, **kwargs)

    def update_invoice(self, **kwargs):
        return data_entry.update_invoice(self.work_item_repo, self.invoice_repo, self.client_repo, **kwargs)

    def mark_ready_for_review(self, **kwargs):
        return data_entry.mark_ready_for_review(self.work_item_repo, **kwargs)

    def send_back_for_correction(self, **kwargs):
        return data_entry.send_back_for_correction(self.work_item_repo, **kwargs)

    # ── Filing ───────────────────────────────────────────────────────────────

    def file_vat_return(self, **kwargs):
        return filing.file_vat_return(self.work_item_repo, **kwargs)

    # ── Queries ──────────────────────────────────────────────────────────────

    def get_work_item(self, item_id: int):
        return vat_report_queries.get_work_item(self.work_item_repo, item_id)

    def list_client_work_items(self, client_id: int):
        return vat_report_queries.list_client_work_items(self.work_item_repo, client_id)

    def list_work_items_by_status(self, **kwargs):
        return vat_report_queries.list_work_items_by_status(
            self.work_item_repo, self.business_repo, **kwargs
        )

    def list_all_work_items(self, **kwargs):
        return vat_report_queries.list_all_work_items(
            self.work_item_repo, self.business_repo, **kwargs
        )

    def list_invoices(self, **kwargs):
        return vat_report_queries.list_invoices(self.invoice_repo, **kwargs)

    def get_work_item_by_client_period(self, client_id: int, period: str):
        return self.work_item_repo.get_by_client_period(client_id, period)

    def get_audit_trail(self, item_id: int):
        return vat_report_queries.get_audit_trail(self.work_item_repo, item_id)

    def get_work_item_enriched(self, item_id: int) -> dict:
        return vat_report_enrichment.get_work_item_enriched(
            self.work_item_repo, self.client_repo, self.user_repo, item_id
        )

    def get_client_items_enriched(self, client_id: int) -> dict:
        return vat_report_enrichment.get_client_items_enriched(
            self.work_item_repo, self.client_repo, self.user_repo, client_id
        )

    def get_list_enriched(self, **kwargs) -> dict:
        return vat_report_enrichment.get_list_enriched(
            self.work_item_repo, self.client_repo, self.user_repo, **kwargs
        )

    def get_audit_trail_enriched(self, item_id: int) -> dict:
        return vat_report_enrichment.get_audit_trail_enriched(
            self.work_item_repo, self.user_repo, item_id
        )
