from datetime import date

from app.clients.models.client import Client, ClientStatus, ClientType
from app.clients.services.client_service import ClientService


def _create_client(db, name: str, id_number: str, status: ClientStatus) -> Client:
    client = Client(
        full_name=name,
        id_number=id_number,
        client_type=ClientType.COMPANY,
        status=status,
        opened_at=date(2024, 1, 1),
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def test_list_all_clients_returns_sorted_non_deleted(test_db):
    _create_client(test_db, "Zebra Corp", "C100", ClientStatus.ACTIVE)
    _create_client(test_db, "Alpha LLC", "C101", ClientStatus.FROZEN)

    service = ClientService(test_db)
    clients = service.list_all_clients()

    assert [c.full_name for c in clients] == ["Alpha LLC", "Zebra Corp"]
    assert all(c.deleted_at is None for c in clients)


def test_list_all_clients_filters_by_status(test_db):
    _create_client(test_db, "Active One", "C200", ClientStatus.ACTIVE)
    _create_client(test_db, "Closed One", "C201", ClientStatus.CLOSED)

    service = ClientService(test_db)
    closed_clients = service.list_all_clients(status=ClientStatus.CLOSED)

    assert len(closed_clients) == 1
    assert closed_clients[0].status == ClientStatus.CLOSED
