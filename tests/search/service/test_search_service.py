from datetime import date
from types import SimpleNamespace

from app.search.services.search_service import SearchService


def test_search_service_mixed_client_and_binder_filters(monkeypatch, test_db):
    svc = SearchService(test_db)
    svc.client_repo = SimpleNamespace(
        search=lambda **kwargs: ([SimpleNamespace(id=1, office_client_number=101, full_name="Alpha", id_number="123", status=SimpleNamespace(value="active"))], 1),
        list_by_ids=lambda ids: [SimpleNamespace(id=1, office_client_number=101, full_name="Alpha", id_number="123", status=SimpleNamespace(value="active"))],
    )
    binder = SimpleNamespace(id=2, client_id=1, binder_number="B-1")
    svc.binder_repo = SimpleNamespace(
        list_active=lambda **kwargs: [binder],
        map_active_by_clients=lambda ids: {1: binder},
    )
    monkeypatch.setattr(
        "app.search.services.search_service.DocumentSearchService",
        lambda db: SimpleNamespace(search_documents=lambda query: [{"id": 10}]),
    )

    items, total, docs = svc.search(query="alpha", binder_number="B-", page=1, page_size=10)
    assert docs == [{"id": 10}]
    assert total >= 1
    assert any(i["result_type"] == "binder" for i in items)


def test_search_service_client_only_short_circuit(test_db):
    svc = SearchService(test_db)
    svc.client_repo = SimpleNamespace(
        search=lambda **kwargs: ([SimpleNamespace(id=1, office_client_number=101, full_name="Alpha", id_number="123", status=SimpleNamespace(value="active"))], 1),
    )
    svc.binder_repo = SimpleNamespace(map_active_by_clients=lambda ids: {})

    items, total, docs = svc.search(query="alpha", page=1, page_size=10)
    assert total == 1
    assert docs == []
    assert items[0]["result_type"] == "client"
