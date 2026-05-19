from types import SimpleNamespace

from app.search.services.search_service import SearchService


def test_search_service_mixed_client_and_binder_filters(monkeypatch, test_db):
    svc = SearchService(test_db)
    svc.client_record_repo = SimpleNamespace(
        search=lambda **kwargs: (
            [
                SimpleNamespace(
                    id=1,
                    legal_entity_id=100,
                    office_client_number=100101,
                    status=SimpleNamespace(value="active"),
                )
            ],
            1,
        ),
        list_by_ids=lambda ids: [
            SimpleNamespace(
                id=1,
                legal_entity_id=100,
                office_client_number=100101,
                status=SimpleNamespace(value="active"),
            )
        ],
    )
    binder = SimpleNamespace(id=2, client_record_id=1, binder_number="B-1")
    business = SimpleNamespace(legal_entity_id=100, full_name="Alpha")
    svc.legal_entity_repo = SimpleNamespace(
        get_by_id=lambda legal_id: SimpleNamespace(
            id=legal_id, official_name="Alpha", id_number="123"
        )
    )
    svc.business_repo = SimpleNamespace(list_by_legal_entity_ids=lambda ids: [business])
    svc.binder_repo = SimpleNamespace(
        list_active=lambda **kwargs: [binder],
        map_active_by_clients=lambda ids: {1: binder},
    )
    monkeypatch.setattr(
        "app.search.services.search_service.DocumentSearchService",
        lambda db: SimpleNamespace(search_documents=lambda query, filename=None: [{"id": 10}]),
    )

    items, total, docs = svc.search(query="alpha", binder_number="B-", page=1, page_size=10)
    assert docs == [{"id": 10}]
    assert total >= 1
    assert any(i["result_type"] == "binder" for i in items)


def test_search_service_client_only_short_circuit(test_db):
    svc = SearchService(test_db)
    client_record = SimpleNamespace(
        id=1,
        legal_entity_id=100,
        office_client_number=100101,
        status=SimpleNamespace(value="active"),
    )
    svc.client_record_repo = SimpleNamespace(
        search=lambda **kwargs: ([client_record], 1),
        list_by_ids=lambda ids: [client_record],
    )
    svc.legal_entity_repo = SimpleNamespace(
        get_by_id=lambda legal_id: SimpleNamespace(
            id=legal_id, official_name="Alpha", id_number="123"
        )
    )
    svc.binder_repo = SimpleNamespace(
        map_active_by_clients=lambda ids: {},
        list_active=lambda **kwargs: [],
    )

    items, total, docs = svc.search(query="alpha", page=1, page_size=10)
    assert total == 1
    assert docs == []
    assert items[0]["result_type"] == "client"
