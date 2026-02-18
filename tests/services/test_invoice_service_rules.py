from datetime import UTC, date, datetime

import pytest

from app.models import Client, ClientType
from app.charge.services.billing_service import BillingService
from app.invoice.services.invoice_service import InvoiceService


def _create_client(test_db) -> Client:
    client = Client(
        full_name="Client C",
        id_number="333333333",
        client_type=ClientType.EMPLOYEE,
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    return client


def test_attach_invoice_succeeds_only_for_issued_charge(test_db):
    c = _create_client(test_db)
    billing = BillingService(test_db)
    invoices = InvoiceService(test_db)

    draft = billing.create_charge(c.id, 10.0, "one_time")
    with pytest.raises(ValueError, match="status draft"):
        invoices.attach_invoice_to_charge(
            draft.id, "icount", "INV-1", issued_at=datetime.now(UTC).replace(tzinfo=None)
        )

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
    with pytest.raises(ValueError, match="status paid"):
        invoices.attach_invoice_to_charge(
            issued.id, "icount", "INV-3", issued_at=datetime.now(UTC).replace(tzinfo=None)
        )

    canceled_id = billing.issue_charge(billing.create_charge(c.id, 30.0, "one_time").id).id
    billing.cancel_charge(canceled_id)
    with pytest.raises(ValueError, match="status canceled"):
        invoices.attach_invoice_to_charge(
            canceled_id, "icount", "INV-4", issued_at=datetime.now(UTC).replace(tzinfo=None)
        )


def test_attach_invoice_fails_if_already_attached(test_db):
    c = _create_client(test_db)
    billing = BillingService(test_db)
    invoices = InvoiceService(test_db)

    ch = billing.issue_charge(billing.create_charge(c.id, 20.0, "retainer").id)
    invoices.attach_invoice_to_charge(
        ch.id, "icount", "INV-10", issued_at=datetime.now(UTC).replace(tzinfo=None)
    )
    with pytest.raises(ValueError, match="already has an invoice"):
        invoices.attach_invoice_to_charge(
            ch.id, "icount", "INV-11", issued_at=datetime.now(UTC).replace(tzinfo=None)
        )
