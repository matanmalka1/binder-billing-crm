from app.clients.models.client import IdNumberType
from app.clients.services.client_service import ClientService


def test_list_all_clients_returns_only_active_sorted(test_db):
    service = ClientService(test_db)
    b = service.create_client(
        full_name="B Client",
        id_number="680000002",
        id_number_type=IdNumberType.CORPORATION,
    )
    a = service.create_client(
        full_name="A Client",
        id_number="680000001",
        id_number_type=IdNumberType.CORPORATION,
    )
    d = service.create_client(
        full_name="D Client",
        id_number="680000004",
        id_number_type=IdNumberType.CORPORATION,
    )

    service.delete_client(d.id, actor_id=1)

    items = service.list_all_clients()

    assert [c.id for c in items] == [a.id, b.id]
