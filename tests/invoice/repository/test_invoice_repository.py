from datetime import date, datetime, timezone
from decimal import Decimal

from app.businesses.models.business import Business, EntityType
from app.charge.models.charge import ChargeType
from app.charge.repositories.charge_repository import ChargeRepository
from app.clients.models.client import Client
from app.invoice.repositories.invoice_repository import InvoiceRepository


def _business(test_db):
    client = Client(
        full_name="Invoice Client",
        id_number="INV001",
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)

    business = Business(
        client_id=client.id,
        entity_type=EntityType.COMPANY_LTD,
        opened_at=date(2024, 1, 1),
    )
    test_db.add(business)
    test_db.commit()
    test_db.refresh(business)
    return business


def test_invoice_repository_getters(test_db):
    business = _business(test_db)
    charge_repo = ChargeRepository(test_db)
    invoice_repo = InvoiceRepository(test_db)

    charge = charge_repo.create(
        business_id=business.id,
        amount=Decimal("123.45"),
        charge_type=ChargeType.MONTHLY_RETAINER,
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
    assert "<Invoice(" in repr(created)

    assert invoice_repo.get_by_charge_id(9999) is None
    assert invoice_repo.exists_for_charge(9999) is False


def test_invoice_repository_list_by_charge_ids(test_db):
    business = _business(test_db)
    charge_repo = ChargeRepository(test_db)
    invoice_repo = InvoiceRepository(test_db)

    charge_a = charge_repo.create(
        business_id=business.id,
        amount=Decimal("10.00"),
        charge_type=ChargeType.CONSULTATION_FEE,
    )
    charge_b = charge_repo.create(
        business_id=business.id,
        amount=Decimal("20.00"),
        charge_type=ChargeType.OTHER,
    )

    inv_a = invoice_repo.create(
        charge_id=charge_a.id,
        provider="icount",
        external_invoice_id="INV-A",
        issued_at=datetime(2026, 2, 1, 10, 0, 0),
    )
    invoice_repo.create(
        charge_id=charge_b.id,
        provider="icount",
        external_invoice_id="INV-B",
        issued_at=datetime(2026, 2, 2, 10, 0, 0),
    )

    listed = invoice_repo.list_by_charge_ids([charge_a.id])
    assert [inv.id for inv in listed] == [inv_a.id]
    assert invoice_repo.list_by_charge_ids([]) == []
