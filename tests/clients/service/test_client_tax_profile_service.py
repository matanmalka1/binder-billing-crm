from datetime import date

import pytest

from app.clients.models.client import Client, ClientType
from app.clients.models.client_tax_profile import VatType
from app.clients.services.client_tax_profile_service import ClientTaxProfileService
from app.core.exceptions import NotFoundError


def _client(test_db) -> Client:
    client = Client(
        full_name="Tax Profile Service Client",
        id_number="CTS001",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    return client


def test_get_profile_and_update_profile_flow(test_db):
    client = _client(test_db)
    service = ClientTaxProfileService(test_db)

    assert service.get_profile(client.id) is None

    created = service.update_profile(
        client.id,
        vat_type=VatType.MONTHLY,
        business_type="llc",
        tax_year_start=1,
        accountant_name="CPA A",
    )
    assert created.client_id == client.id
    assert created.vat_type == VatType.MONTHLY
    assert created.updated_at is None

    updated = service.update_profile(
        client.id,
        vat_type=VatType.BIMONTHLY,
        accountant_name="CPA B",
    )
    assert updated.vat_type == VatType.BIMONTHLY
    assert updated.accountant_name == "CPA B"
    assert updated.updated_at is not None
    assert service.get_profile(client.id).id == updated.id


def test_update_profile_unknown_client_raises_not_found(test_db):
    service = ClientTaxProfileService(test_db)
    with pytest.raises(NotFoundError) as exc_info:
        service.update_profile(999999, vat_type=VatType.EXEMPT)
    assert exc_info.value.code == "CLIENT.NOT_FOUND"

