from datetime import date

from app.binders.models.binder import BinderType
from app.binders.repositories.binder_repository import BinderRepository
from app.clients.models import Client, ClientType


def _client(test_db) -> Client:
    client = Client(
        full_name="Client Binders API Client",
        id_number="CBA001",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    return client


def test_list_client_binders_endpoint(client, test_db, advisor_headers, test_user):
    crm_client = _client(test_db)
    binder = BinderRepository(test_db).create(
        client_id=crm_client.id,
        binder_number="CBA-B-001",
        binder_type=BinderType.OTHER,
        received_at=date.today(),
        received_by=test_user.id,
    )

    response = client.get(
        f"/api/v1/clients/{crm_client.id}/binders",
        headers=advisor_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == binder.id
    assert payload["items"][0]["binder_number"] == "CBA-B-001"


def test_list_client_binders_endpoint_returns_404_for_missing_client(client, advisor_headers):
    response = client.get(
        "/api/v1/clients/999999/binders",
        headers=advisor_headers,
    )
    assert response.status_code == 404
