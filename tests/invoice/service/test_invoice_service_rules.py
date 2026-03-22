from datetime import UTC, date, datetime

import pytest

from app.businesses.models.business import Business, BusinessType
from app.clients.models.client import Client
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.charge.services.billing_service import BillingService
from app.invoice.services.invoice_service import InvoiceService


def _create_business(test_db) -> Business:
    client = Client(
        full_name="Client C",
        id_number="333333333",
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)

    business = Business(
        client_id=client.id,
        business_type=BusinessType.EMPLOYEE,
        opened_at=date.today(),
    )
    test_db.add(business)
    test_db.commit()
    test_db.refresh(business)
    return business


def test_attach_invoice_succeeds_only_for_issued_charge(test_db):
    business = _create_business(test_db)
    billing = BillingService(test_db)
    invoices = InvoiceService(test_db)

    draft = billing.create_charge(business.id, 10.0, "consultation_fee")
    with pytest.raises(AppError) as exc_info:
        invoices.attach_invoice_to_charge(
            draft.id, "icount", "INV-1", issued_at=datetime.now(UTC).replace(tzinfo=None)
        )
    assert exc_info.value.code == "INVOICE.INVALID_STATUS"

    issued = billing.issue_charge(draft.id)
    inv = invoices.attach_invoice_to_charge(
        issued.id,
        provider="icount",
        external_invoice_id="INV-2",
        issued_at=datetime(2026, 2, 1, 10, 0, 0),
        document_url="https://example.com/invoice/INV-2",
    )
    assert inv.charge_id == issued.id
    assert inv.external_invoice_id == "INV-2"

    billing.mark_charge_paid(issued.id)
    with pytest.raises(AppError) as exc_info:
        invoices.attach_invoice_to_charge(
            issued.id, "icount", "INV-3", issued_at=datetime.now(UTC).replace(tzinfo=None)
        )
    assert exc_info.value.code == "INVOICE.INVALID_STATUS"

    canceled_id = billing.issue_charge(
        billing.create_charge(business.id, 30.0, "consultation_fee").id
    ).id
    billing.cancel_charge(canceled_id)
    with pytest.raises(AppError) as exc_info:
        invoices.attach_invoice_to_charge(
            canceled_id, "icount", "INV-4", issued_at=datetime.now(UTC).replace(tzinfo=None)
        )
    assert exc_info.value.code == "INVOICE.INVALID_STATUS"


def test_attach_invoice_fails_if_already_attached(test_db):
    business = _create_business(test_db)
    billing = BillingService(test_db)
    invoices = InvoiceService(test_db)

    ch = billing.issue_charge(billing.create_charge(business.id, 20.0, "monthly_retainer").id)
    invoices.attach_invoice_to_charge(
        ch.id, "icount", "INV-10", issued_at=datetime.now(UTC).replace(tzinfo=None)
    )
    with pytest.raises(ConflictError) as exc_info:
        invoices.attach_invoice_to_charge(
            ch.id, "icount", "INV-11", issued_at=datetime.now(UTC).replace(tzinfo=None)
        )
    assert exc_info.value.code == "INVOICE.CONFLICT"


def test_attach_invoice_missing_charge_returns_not_found(test_db):
    invoices = InvoiceService(test_db)
    with pytest.raises(NotFoundError) as exc_info:
        invoices.attach_invoice_to_charge(
            999999,
            provider="icount",
            external_invoice_id="INV-MISSING",
            issued_at=datetime(2026, 1, 1, 12, 0, 0),
        )
    assert exc_info.value.code == "INVOICE.NOT_FOUND"
