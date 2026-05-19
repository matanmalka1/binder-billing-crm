from datetime import datetime
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import AppError, ConflictError
from app.vat_reports.models.vat_enums import (
    DocumentType,
    ExpenseCategory,
    InvoiceType,
    VatWorkItemStatus,
)
from app.vat_reports.services.data_entry_invoices import add_invoice
from tests.vat_reports.service.test_vat_report_test_utils import make_invoice, make_item


class TestAddInvoice:
    def _add_income(self, work_item_repo, invoice_repo, status=VatWorkItemStatus.MATERIAL_RECEIVED):
        item = make_item(status=status)
        work_item_repo.get_by_id.return_value = item
        invoice_repo.get_by_number.return_value = None
        invoice_repo.create.return_value = make_invoice()
        invoice_repo.sum_vat_both_types.return_value = (170.0, 0.0)
        invoice_repo.sum_net_both_types.return_value = (1000.0, 0.0)

        return add_invoice(
            work_item_repo,
            invoice_repo,
            item_id=1,
            created_by=1,
            invoice_type=InvoiceType.INCOME,
            invoice_number="INV-001",
            invoice_date=datetime(2026, 1, 15),
            counterparty_name="Customer A",
            gross_amount=1180.0,
        )

    def test_happy_path_auto_transitions_status(self):
        work_item_repo = MagicMock()
        invoice_repo = MagicMock()
        self._add_income(work_item_repo, invoice_repo)

        work_item_repo.update_status.assert_called_with(1, VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS)

    def test_negative_gross_amount_raises(self):
        work_item_repo = MagicMock()
        invoice_repo = MagicMock()
        work_item_repo.get_by_id.return_value = make_item()

        with pytest.raises(AppError) as exc_info:
            add_invoice(
                work_item_repo,
                invoice_repo,
                item_id=1,
                created_by=1,
                invoice_type=InvoiceType.INCOME,
                invoice_number="INV-002",
                invoice_date=datetime(2026, 1, 15),
                counterparty_name="Customer B",
                gross_amount=-1.0,
            )
        assert exc_info.value.code == "VAT.NET_NOT_POSITIVE"

    def test_zero_gross_amount_raises(self):
        work_item_repo = MagicMock()
        invoice_repo = MagicMock()
        work_item_repo.get_by_id.return_value = make_item()

        with pytest.raises(AppError) as exc_info:
            add_invoice(
                work_item_repo,
                invoice_repo,
                item_id=1,
                created_by=1,
                invoice_type=InvoiceType.INCOME,
                invoice_number="INV-003",
                invoice_date=datetime(2026, 1, 15),
                counterparty_name="Customer C",
                gross_amount=0.0,
            )
        assert exc_info.value.code == "VAT.NET_NOT_POSITIVE"

    def test_expense_without_category_raises(self):
        work_item_repo = MagicMock()
        invoice_repo = MagicMock()
        work_item_repo.get_by_id.return_value = make_item()

        with pytest.raises(AppError) as exc_info:
            add_invoice(
                work_item_repo,
                invoice_repo,
                item_id=1,
                created_by=1,
                invoice_type=InvoiceType.EXPENSE,
                invoice_number="EXP-001",
                invoice_date=datetime(2026, 1, 15),
                counterparty_name="Supplier A",
                gross_amount=590.0,
            )
        assert exc_info.value.code == "VAT.EXPENSE_CATEGORY_REQUIRED"

    def test_expense_tax_invoice_without_counterparty_id_raises(self):
        work_item_repo = MagicMock()
        invoice_repo = MagicMock()
        work_item_repo.get_by_id.return_value = make_item()

        with pytest.raises(AppError) as exc_info:
            add_invoice(
                work_item_repo,
                invoice_repo,
                item_id=1,
                created_by=1,
                invoice_type=InvoiceType.EXPENSE,
                invoice_number="EXP-TAX-001",
                invoice_date=datetime(2026, 1, 15),
                counterparty_name="Supplier B",
                gross_amount=590.0,
                expense_category=ExpenseCategory.OFFICE,
                document_type=DocumentType.TAX_INVOICE,
            )
        assert exc_info.value.code == "VAT.COUNTERPARTY_ID_REQUIRED"

    def test_duplicate_invoice_number_raises(self):
        work_item_repo = MagicMock()
        invoice_repo = MagicMock()
        work_item_repo.get_by_id.return_value = make_item()
        invoice_repo.get_by_number.return_value = make_invoice()

        with pytest.raises(ConflictError) as exc_info:
            add_invoice(
                work_item_repo,
                invoice_repo,
                item_id=1,
                created_by=1,
                invoice_type=InvoiceType.INCOME,
                invoice_number="INV-001",
                invoice_date=datetime(2026, 1, 15),
                counterparty_name="Customer",
                gross_amount=1180.0,
            )
        assert exc_info.value.code == "VAT.CONFLICT"

    def test_cannot_add_to_filed_item(self):
        work_item_repo = MagicMock()
        invoice_repo = MagicMock()
        work_item_repo.get_by_id.return_value = make_item(status=VatWorkItemStatus.FILED)

        with pytest.raises(AppError) as exc_info:
            add_invoice(
                work_item_repo,
                invoice_repo,
                item_id=1,
                created_by=1,
                invoice_type=InvoiceType.INCOME,
                invoice_number="INV-099",
                invoice_date=datetime(2026, 1, 15),
                counterparty_name="Customer",
                gross_amount=590.0,
            )
        assert exc_info.value.code == "VAT.FILED_IMMUTABLE"
