from app.clients.services.client_service import ClientService
from app.common.enums import IdNumberType


def test_list_all_clients_returns_only_active_sorted(test_db):
    service = ClientService(test_db)
    b = service.create_client(
        full_name="B Client",
        id_number="680000007",
        id_number_type=IdNumberType.CORPORATION,
        actor_id=1,
    )
    a = service.create_client(
        full_name="A Client",
        id_number="680000015",
        id_number_type=IdNumberType.CORPORATION,
        actor_id=1,
    )
    d = service.create_client(
        full_name="D Client",
        id_number="680000023",
        id_number_type=IdNumberType.CORPORATION,
        actor_id=1,
    )

    service.delete_client(d.id, actor_id=1)

    items = service.list_all_clients()

    assert [c.id for c in items] == [a.id, b.id]
