"""
Unit tests for the VAT Reports service layer.

Covers:
  - Work item creation (normal, pending, duplicate prevention)
  - Materials complete transition
  - Invoice add (income, expense, validation rules)
  - Invoice delete
  - Status transitions (mark ready, send back)
  - Filing (normal, override, guard rails)
  - Audit trail
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from app.vat_reports.models.vat_enums import (
    ExpenseCategory,
    FilingMethod,
    InvoiceType,
    VatWorkItemStatus,
)
from app.vat_reports.services import data_entry, filing, intake


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_item(
    id: int = 1,
    client_id: int = 10,
    period: str = "2026-01",
    status: VatWorkItemStatus = VatWorkItemStatus.MATERIAL_RECEIVED,
    net_vat: float = 0,
):
    item = MagicMock()
    item.id = id
    item.client_id = client_id
    item.period = period
    item.status = status
    item.net_vat = net_vat
    return item


def _make_invoice(id: int = 1, work_item_id: int = 1, invoice_type=InvoiceType.INCOME):
    inv = MagicMock()
    inv.id = id
    inv.work_item_id = work_item_id
    inv.invoice_type = invoice_type
    inv.invoice_number = "INV-001"
    inv.vat_amount = 170
    return inv


# ─── intake.create_work_item ──────────────────────────────────────────────────

class TestCreateWorkItem:
    def test_happy_path_material_received(self):
        work_item_repo = MagicMock()
        client_repo = MagicMock()

        client_repo.get_by_id.return_value = MagicMock()  # client exists
        work_item_repo.get_by_client_period.return_value = None  # no duplicate
        work_item_repo.create.return_value = _make_item()

        result = intake.create_work_item(
            work_item_repo,
            client_repo,
            client_id=10,
            period="2026-01",
            created_by=1,
        )

        work_item_repo.create.assert_called_once()
        work_item_repo.append_audit.assert_called_once()
        assert result.status == VatWorkItemStatus.MATERIAL_RECEIVED

    def test_client_not_found_raises(self):
        work_item_repo = MagicMock()
        client_repo = MagicMock()
        client_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="not found"):
            intake.create_work_item(
                work_item_repo, client_repo, client_id=99, period="2026-01", created_by=1
            )

    def test_duplicate_period_raises(self):
        work_item_repo = MagicMock()
        client_repo = MagicMock()
        client_repo.get_by_id.return_value = MagicMock()
        work_item_repo.get_by_client_period.return_value = _make_item()

        with pytest.raises(ValueError, match="already exists"):
            intake.create_work_item(
                work_item_repo, client_repo, client_id=10, period="2026-01", created_by=1
            )

    def test_pending_without_note_raises(self):
        work_item_repo = MagicMock()
        client_repo = MagicMock()
        client_repo.get_by_id.return_value = MagicMock()
        work_item_repo.get_by_client_period.return_value = None

        with pytest.raises(ValueError, match="pending_materials_note"):
            intake.create_work_item(
                work_item_repo,
                client_repo,
                client_id=10,
                period="2026-01",
                created_by=1,
                mark_pending=True,
            )

    def test_pending_with_note_creates_item(self):
        work_item_repo = MagicMock()
        client_repo = MagicMock()
        client_repo.get_by_id.return_value = MagicMock()
        work_item_repo.get_by_client_period.return_value = None
        pending_item = _make_item(status=VatWorkItemStatus.PENDING_MATERIALS)
        work_item_repo.create.return_value = pending_item

        result = intake.create_work_item(
            work_item_repo,
            client_repo,
            client_id=10,
            period="2026-01",
            created_by=1,
            mark_pending=True,
            pending_materials_note="Missing Q4 invoices",
        )
        assert result.status == VatWorkItemStatus.PENDING_MATERIALS


# ─── intake.mark_materials_complete ──────────────────────────────────────────

class TestMarkMaterialsComplete:
    def test_happy_path(self):
        work_item_repo = MagicMock()
        item = _make_item(status=VatWorkItemStatus.PENDING_MATERIALS)
        work_item_repo.get_by_id.return_value = item
        work_item_repo.update_status.return_value = _make_item(
            status=VatWorkItemStatus.MATERIAL_RECEIVED
        )

        result = intake.mark_materials_complete(
            work_item_repo, item_id=1, performed_by=1
        )
        assert result.status == VatWorkItemStatus.MATERIAL_RECEIVED

    def test_wrong_status_raises(self):
        work_item_repo = MagicMock()
        work_item_repo.get_by_id.return_value = _make_item(
            status=VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS
        )

        with pytest.raises(ValueError, match="Cannot mark materials complete"):
            intake.mark_materials_complete(work_item_repo, item_id=1, performed_by=1)


# ─── data_entry.add_invoice ──────────────────────────────────────────────────

class TestAddInvoice:
    def _add_income(self, work_item_repo, invoice_repo, status=VatWorkItemStatus.MATERIAL_RECEIVED):
        item = _make_item(status=status)
        work_item_repo.get_by_id.return_value = item
        invoice_repo.get_by_number.return_value = None
        invoice_repo.create.return_value = _make_invoice()
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
        result = self._add_income(work_item_repo, invoice_repo)

        # Should auto-transition MATERIAL_RECEIVED → DATA_ENTRY_IN_PROGRESS
        work_item_repo.update_status.assert_called_with(
            1, VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS
        )
        assert result.id == 1

    def test_negative_vat_raises(self):
        work_item_repo = MagicMock()
        invoice_repo = MagicMock()
        work_item_repo.get_by_id.return_value = _make_item()

        with pytest.raises(ValueError, match="negative"):
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

    def test_zero_net_amount_raises(self):
        work_item_repo = MagicMock()
        invoice_repo = MagicMock()
        work_item_repo.get_by_id.return_value = _make_item()

        with pytest.raises(ValueError, match="positive"):
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

    def test_expense_without_category_raises(self):
        work_item_repo = MagicMock()
        invoice_repo = MagicMock()
        work_item_repo.get_by_id.return_value = _make_item()

        with pytest.raises(ValueError, match="expense_category"):
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

    def test_duplicate_invoice_number_raises(self):
        work_item_repo = MagicMock()
        invoice_repo = MagicMock()
        work_item_repo.get_by_id.return_value = _make_item()
        invoice_repo.get_by_number.return_value = _make_invoice()  # already exists

        with pytest.raises(ValueError, match="already exists"):
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

    def test_cannot_add_to_filed_item(self):
        work_item_repo = MagicMock()
        invoice_repo = MagicMock()
        work_item_repo.get_by_id.return_value = _make_item(
            status=VatWorkItemStatus.FILED
        )

        with pytest.raises(ValueError, match="filed"):
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


# ─── data_entry.mark_ready_for_review ────────────────────────────────────────

class TestMarkReadyForReview:
    def test_happy_path(self):
        work_item_repo = MagicMock()
        work_item_repo.get_by_id.return_value = _make_item(
            status=VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS
        )
        work_item_repo.update_status.return_value = _make_item(
            status=VatWorkItemStatus.READY_FOR_REVIEW
        )

        result = data_entry.mark_ready_for_review(
            work_item_repo, item_id=1, performed_by=1
        )
        assert result.status == VatWorkItemStatus.READY_FOR_REVIEW

    def test_wrong_status_raises(self):
        work_item_repo = MagicMock()
        work_item_repo.get_by_id.return_value = _make_item(
            status=VatWorkItemStatus.MATERIAL_RECEIVED
        )

        with pytest.raises(ValueError, match="Cannot mark ready for review"):
            data_entry.mark_ready_for_review(work_item_repo, item_id=1, performed_by=1)


# ─── data_entry.send_back_for_correction ────────────────────────────────────

class TestSendBackForCorrection:
    def test_happy_path(self):
        work_item_repo = MagicMock()
        work_item_repo.get_by_id.return_value = _make_item(
            status=VatWorkItemStatus.READY_FOR_REVIEW
        )
        work_item_repo.update_status.return_value = _make_item(
            status=VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS
        )

        result = data_entry.send_back_for_correction(
            work_item_repo,
            item_id=1,
            performed_by=1,
            correction_note="Invoice #5 is missing counterparty ID",
        )
        assert result.status == VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS
        # Note must be logged
        work_item_repo.append_audit.assert_called_once()

    def test_empty_note_raises(self):
        work_item_repo = MagicMock()

        with pytest.raises(ValueError, match="correction_note"):
            data_entry.send_back_for_correction(
                work_item_repo, item_id=1, performed_by=1, correction_note="   "
            )


# ─── filing.file_vat_return ───────────────────────────────────────────────────

class TestFileVatReturn:
    def test_happy_path_system_calculated(self):
        work_item_repo = MagicMock()
        item = _make_item(status=VatWorkItemStatus.READY_FOR_REVIEW, net_vat=500.0)
        work_item_repo.get_by_id.return_value = item
        filed_item = _make_item(status=VatWorkItemStatus.FILED)
        work_item_repo.mark_filed.return_value = filed_item

        result = filing.file_vat_return(
            work_item_repo,
            item_id=1,
            filed_by=2,
            filing_method=FilingMethod.ONLINE,
        )

        work_item_repo.mark_filed.assert_called_once_with(
            item_id=1,
            final_vat_amount=500.0,
            filing_method=FilingMethod.ONLINE,
            filed_by=2,
            is_overridden=False,
            override_justification=None,
        )
        assert result.status == VatWorkItemStatus.FILED

    def test_override_without_justification_raises(self):
        work_item_repo = MagicMock()
        work_item_repo.get_by_id.return_value = _make_item(
            status=VatWorkItemStatus.READY_FOR_REVIEW
        )

        with pytest.raises(ValueError, match="justification"):
            filing.file_vat_return(
                work_item_repo,
                item_id=1,
                filed_by=2,
                filing_method=FilingMethod.MANUAL,
                override_amount=1000.0,
                override_justification=None,
            )

    def test_override_with_justification_logged(self):
        work_item_repo = MagicMock()
        item = _make_item(status=VatWorkItemStatus.READY_FOR_REVIEW, net_vat=300.0)
        work_item_repo.get_by_id.return_value = item
        work_item_repo.mark_filed.return_value = _make_item(status=VatWorkItemStatus.FILED)

        filing.file_vat_return(
            work_item_repo,
            item_id=1,
            filed_by=2,
            filing_method=FilingMethod.MANUAL,
            override_amount=400.0,
            override_justification="Client provided corrected invoice post-review",
        )

        work_item_repo.mark_filed.assert_called_once_with(
            item_id=1,
            final_vat_amount=400.0,
            filing_method=FilingMethod.MANUAL,
            filed_by=2,
            is_overridden=True,
            override_justification="Client provided corrected invoice post-review",
        )
        # Two audit entries: override log + filed log
        assert work_item_repo.append_audit.call_count == 2

    def test_wrong_status_raises(self):
        work_item_repo = MagicMock()
        work_item_repo.get_by_id.return_value = _make_item(
            status=VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS
        )

        with pytest.raises(ValueError, match="READY_FOR_REVIEW"):
            filing.file_vat_return(
                work_item_repo,
                item_id=1,
                filed_by=2,
                filing_method=FilingMethod.ONLINE,
            )

    def test_not_found_raises(self):
        work_item_repo = MagicMock()
        work_item_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="not found"):
            filing.file_vat_return(
                work_item_repo, item_id=999, filed_by=2, filing_method=FilingMethod.ONLINE
            )
