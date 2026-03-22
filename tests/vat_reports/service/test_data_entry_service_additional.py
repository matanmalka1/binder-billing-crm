from datetime import datetime
from types import SimpleNamespace

import pytest

from app.businesses.models.business import BusinessType
from app.core.exceptions import AppError, NotFoundError
from app.vat_reports.models.vat_enums import InvoiceType, VatWorkItemStatus
from app.vat_reports.services.data_entry_common import (
    assert_transition_allowed,
    check_osek_patur_ceiling,
    resolve_invoice_derived_fields,
)
from app.vat_reports.services.data_entry_invoice_delete import delete_invoice
from app.vat_reports.services.data_entry_invoices import add_invoice


def test_add_invoice_not_found_and_invalid_status(monkeypatch):
    business_repo = SimpleNamespace(get_by_id=lambda _id: None)
    work_item_repo = SimpleNamespace(get_by_id=lambda _id: None)
    invoice_repo = SimpleNamespace()
    with pytest.raises(NotFoundError):
        add_invoice(
            work_item_repo,
            invoice_repo,
            business_repo,
            item_id=1,
            created_by=1,
            invoice_type=InvoiceType.INCOME,
            invoice_number=None,
            invoice_date=None,
            counterparty_name=None,
            net_amount=10,
            vat_amount=1.7,
        )

    item = SimpleNamespace(id=1, business_id=1, period="2026-01", status=VatWorkItemStatus.PENDING_MATERIALS)
    work_item_repo = SimpleNamespace(
        db=object(),
        get_by_id=lambda _id: item,
        update_status=lambda *args, **kwargs: None,
        append_audit=lambda **kwargs: None,
    )
    invoice_repo = SimpleNamespace(get_by_number=lambda *args, **kwargs: None)
    with pytest.raises(AppError):
        add_invoice(
            work_item_repo,
            invoice_repo,
            business_repo,
            item_id=1,
            created_by=1,
            invoice_type=InvoiceType.INCOME,
            invoice_number=None,
            invoice_date=None,
            counterparty_name=None,
            net_amount=10,
            vat_amount=1.7,
        )


def test_add_invoice_autofill_fields_for_income_and_expense(monkeypatch):
    item = SimpleNamespace(id=1, business_id=1, period="2026-03", status=VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS)
    created = {}
    work_item_repo = SimpleNamespace(
        db=object(),
        get_by_id=lambda _id: item,
        update_status=lambda *args, **kwargs: None,
        append_audit=lambda **kwargs: None,
    )
    invoice_repo = SimpleNamespace(
        get_by_number=lambda *args, **kwargs: None,
        create=lambda **kwargs: created.setdefault("invoice", SimpleNamespace(id=44, **kwargs)),
    )
    business_repo = SimpleNamespace(get_by_id=lambda _id: None)
    monkeypatch.setattr(
        "app.vat_reports.services.data_entry_invoices.recalculate_totals",
        lambda *args, **kwargs: None,
    )

    income = add_invoice(
        work_item_repo,
        invoice_repo,
        business_repo,
        item_id=1,
        created_by=1,
        invoice_type=InvoiceType.INCOME,
        invoice_number=None,
        invoice_date=None,
        counterparty_name=None,
        net_amount=50,
        vat_amount=8.5,
    )
    assert income.counterparty_name == "הכנסות"
    assert income.invoice_date == datetime(2026, 3, 1)


def test_data_entry_common_invalid_transition_and_ceiling():
    item = SimpleNamespace(status=VatWorkItemStatus.PENDING_MATERIALS)
    with pytest.raises(AppError):
        assert_transition_allowed(item, VatWorkItemStatus.FILED)

    osek_business = SimpleNamespace(business_type=BusinessType.OSEK_PATUR)

    class _InvoiceRepo:
        def sum_income_net_by_business_year(self, business_id, year):
            return 2000000

    with pytest.raises(AppError):
        check_osek_patur_ceiling(osek_business, _InvoiceRepo(), 1, "2026-01", 1)

    derived = resolve_invoice_derived_fields(
        invoice_type=InvoiceType.INCOME,
        expense_category=None,
        document_type=None,
        counterparty_id=None,
        net_amount=100,
        vat_amount=17,
    )
    assert "deduction_rate" in derived


def test_delete_invoice_not_found_paths():
    work_item_repo = SimpleNamespace(get_by_id=lambda _id: None)
    invoice_repo = SimpleNamespace()
    with pytest.raises(NotFoundError):
        delete_invoice(work_item_repo, invoice_repo, item_id=1, invoice_id=1, performed_by=1)
