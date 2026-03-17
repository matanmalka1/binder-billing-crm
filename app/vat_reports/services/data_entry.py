"""Facade module for VAT data entry flows (keeps public API stable)."""

from app.vat_reports.services.data_entry_invoice_delete import delete_invoice
from app.vat_reports.services.data_entry_invoice_update import update_invoice
from app.vat_reports.services.data_entry_invoices import add_invoice
from app.vat_reports.services.data_entry_status import (
    mark_ready_for_review,
    send_back_for_correction,
)

__all__ = [
    "add_invoice",
    "delete_invoice",
    "update_invoice",
    "mark_ready_for_review",
    "send_back_for_correction",
]
