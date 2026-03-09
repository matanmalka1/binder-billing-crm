from datetime import datetime
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import AppError, ConflictError
from app.vat_reports.models.vat_enums import ExpenseCategory, InvoiceType, VatWorkItemStatus
from app.vat_reports.services import data_entry
from tests.services.vat_report_test_utils import make_item, make_invoice


class TestAddInvoice:
    def _add_income(self, work_item_repo, invoice_repo, status=VatWorkItemStatus.MATERIAL_RECEIVED):
        item = make_item(status=status)
        work_item_repo.get_by_id.return_value = item
        invoice_repo.get_by_number.return_value = None
        invoice_repo.create.return_value = make_invoice()
        invoice_repo.sum_vat_both_types.return_value = (170.0, 0.0)

        return data_entry.add_invoice(
            work_item_repo,
            invoice_repo,
            item_id=1,
            created_by=1,
            invoice_type=InvoiceType.INCOME,
            invoice_number="INV-001",
            invoice_date=datetime(2026, 1, 15),
            counterparty_name="Customer A",
            net_amount=1000.0,
            vat_amount=170.0,
        )

    def test_happy_path_auto_transitions_status(self):
        work_item_repo = MagicMock()
        invoice_repo = MagicMock()
        self._add_income(work_item_repo, invoice_repo)

        work_item_repo.update_status.assert_called_with(1, VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS)

    def test_negative_vat_raises(self):
        work_item_repo = MagicMock()
        invoice_repo = MagicMock()
        work_item_repo.get_by_id.return_value = make_item()

        with pytest.raises(AppError) as exc_info:
            data_entry.add_invoice(
                work_item_repo,
                invoice_repo,
                item_id=1,
                created_by=1,
                invoice_type=InvoiceType.INCOME,
                invoice_number="INV-002",
                invoice_date=datetime(2026, 1, 15),
                counterparty_name="Customer B",
                net_amount=1000.0,
                vat_amount=-1.0,
            )
        assert exc_info.value.code == "VAT.NEGATIVE_VAT"

    def test_zero_net_amount_raises(self):
        work_item_repo = MagicMock()
        invoice_repo = MagicMock()
        work_item_repo.get_by_id.return_value = make_item()

        with pytest.raises(AppError) as exc_info:
            data_entry.add_invoice(
                work_item_repo,
                invoice_repo,
                item_id=1,
                created_by=1,
                invoice_type=InvoiceType.INCOME,
                invoice_number="INV-003",
                invoice_date=datetime(2026, 1, 15),
                counterparty_name="Customer C",
                net_amount=0.0,
                vat_amount=0.0,
            )
        assert exc_info.value.code == "VAT.NET_NOT_POSITIVE"

    def test_expense_without_category_raises(self):
        work_item_repo = MagicMock()
        invoice_repo = MagicMock()
        work_item_repo.get_by_id.return_value = make_item()

        with pytest.raises(AppError) as exc_info:
            data_entry.add_invoice(
                work_item_repo,
                invoice_repo,
                item_id=1,
                created_by=1,
                invoice_type=InvoiceType.EXPENSE,
                invoice_number="EXP-001",
                invoice_date=datetime(2026, 1, 15),
                counterparty_name="Supplier A",
                net_amount=500.0,
                vat_amount=85.0,
            )
        assert exc_info.value.code == "VAT.EXPENSE_CATEGORY_REQUIRED"

    def test_duplicate_invoice_number_raises(self):
        work_item_repo = MagicMock()
        invoice_repo = MagicMock()
        work_item_repo.get_by_id.return_value = make_item()
        invoice_repo.get_by_number.return_value = make_invoice()  # already exists

        with pytest.raises(ConflictError) as exc_info:
            data_entry.add_invoice(
                work_item_repo,
                invoice_repo,
                item_id=1,
                created_by=1,
                invoice_type=InvoiceType.INCOME,
                invoice_number="INV-001",
                invoice_date=datetime(2026, 1, 15),
                counterparty_name="Customer",
                net_amount=1000.0,
                vat_amount=170.0,
            )
        assert exc_info.value.code == "VAT.CONFLICT"

    def test_cannot_add_to_filed_item(self):
        work_item_repo = MagicMock()
        invoice_repo = MagicMock()
        work_item_repo.get_by_id.return_value = make_item(status=VatWorkItemStatus.FILED)

        with pytest.raises(AppError) as exc_info:
            data_entry.add_invoice(
                work_item_repo,
                invoice_repo,
                item_id=1,
                created_by=1,
                invoice_type=InvoiceType.INCOME,
                invoice_number="INV-099",
                invoice_date=datetime(2026, 1, 15),
                counterparty_name="Customer",
                net_amount=500.0,
                vat_amount=85.0,
            )
        assert exc_info.value.code == "VAT.FILED_IMMUTABLE"
