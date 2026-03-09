from datetime import datetime, timezone
from decimal import Decimal

from app.charge.models.charge import ChargeType
from app.charge.repositories.charge_repository import ChargeRepository
from app.clients.models.client import Client, ClientType
from app.invoice.repositories.invoice_repository import InvoiceRepository


def _client(test_db):
    client = Client(
        full_name="Invoice Client",
        id_number="INV001",
        client_type=ClientType.COMPANY,
        opened_at=datetime(2024, 1, 1, tzinfo=timezone.utc).date(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    return client


def test_invoice_repository_getters(test_db):
    client = _client(test_db)
    charge_repo = ChargeRepository(test_db)
    invoice_repo = InvoiceRepository(test_db)

    charge = charge_repo.create(
        client_id=client.id,
        amount=Decimal("123.45"),
        charge_type=ChargeType.RETAINER,
    )

    created = invoice_repo.create(
        charge_id=charge.id,
        provider="stripe",
        external_invoice_id="INV-EXT-1",
        issued_at=datetime(2024, 3, 1, tzinfo=timezone.utc),
        document_url="https://example.com/inv.pdf",
    )

    assert invoice_repo.get_by_charge_id(charge.id).id == created.id
    assert invoice_repo.exists_for_charge(charge.id) is True
    assert invoice_repo.get_by_id(created.id).external_invoice_id == "INV-EXT-1"

    assert invoice_repo.get_by_charge_id(9999) is None
    assert invoice_repo.exists_for_charge(9999) is False
