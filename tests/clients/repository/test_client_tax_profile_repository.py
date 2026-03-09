from datetime import date
from decimal import Decimal

from app.clients.models.client import ClientType
from app.clients.models.client_tax_profile import VatType
from app.clients.repositories.client_tax_profile_repository import ClientTaxProfileRepository
from app.clients.repositories.client_repository import ClientRepository


def test_upsert_creates_and_updates_profile(test_db):
    client_repo = ClientRepository(test_db)
    profile_repo = ClientTaxProfileRepository(test_db)

    client = client_repo.create(
        full_name="Profile Client",
        id_number="CTP001",
        client_type=ClientType.COMPANY,
        opened_at=date(2024, 1, 1),
    )

    created = profile_repo.upsert(
        client_id=client.id,
        vat_type=VatType.MONTHLY,
        advance_rate=Decimal("12.50"),
        business_type="consulting",
        tax_year_start=2024,
    )
    assert created.vat_type == VatType.MONTHLY
    assert created.advance_rate == Decimal("12.50")

    updated = profile_repo.upsert(
        client_id=client.id,
        vat_type=VatType.BIMONTHLY,
        advance_rate=Decimal("10.00"),
    )
    assert updated.id == created.id
    assert updated.vat_type == VatType.BIMONTHLY
    assert updated.advance_rate == Decimal("10.00")
    assert updated.updated_at is not None

    fetched = profile_repo.get_by_client_id(client.id)
    assert fetched.id == created.id
    assert fetched.vat_type == VatType.BIMONTHLY
