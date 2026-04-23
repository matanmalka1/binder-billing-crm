from datetime import date, timedelta

from app.binders.models.binder import Binder, BinderStatus
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.services.binder_list_service import BinderListService
from app.clients.repositories.client_record_repository import ClientRecordRepository
from tests.helpers.identity import seed_client_identity


def _seed_binders(db, user_id: int):
    c1 = seed_client_identity(
        db,
        full_name="Alpha Client",
        id_number="BLS001",
    )
    c2 = seed_client_identity(
        db,
        full_name="Beta Client",
        id_number="BLS002",
    )

    b1 = Binder(
        client_record_id=c1.id,
        binder_number="AA-100",
        period_start=date.today() - timedelta(days=15),
        status=BinderStatus.IN_OFFICE,
        created_by=user_id,
    )
    b2 = Binder(
        client_record_id=c2.id,
        binder_number="BB-200",
        period_start=date.today() - timedelta(days=5),
        status=BinderStatus.READY_FOR_PICKUP,
        created_by=user_id,
    )
    db.add_all([b1, b2])
    db.commit()
    db.refresh(b1)
    db.refresh(b2)
    return c1, c2, b1, b2


def test_list_binders_enriched_filters_and_invalid_sort_dir(test_db, test_user):
    c1, c2, _b1, _b2 = _seed_binders(test_db, test_user.id)
    service = BinderListService()
    service.db = test_db
    service.binder_repo = BinderRepository(test_db)
    service.client_record_repo = ClientRecordRepository(test_db)

    items, total, counters = service.list_binders_enriched(
        sort_by="client_name",
        sort_dir="invalid",
        query="AA",
        client_name_filter="alpha",
        binder_number="AA",
        year=date.today().year,
        page=1,
        page_size=10,
    )
    assert total == 1
    assert len(items) == 1
    assert items[0].client_name == "Alpha Client"
    assert counters["total"] == 1
    assert counters["in_office"] == 1
    assert counters["closed_in_office"] == 0
    assert counters["archived_in_office"] == 0
    assert counters["ready_for_pickup"] == 0
    assert counters["returned"] == 0

    none_items, none_total, none_counters = service.list_binders_enriched(query="does-not-match")
    assert none_total == 0
    assert none_items == []
    assert none_counters == {
        "total": 0,
        "in_office": 0,
        "closed_in_office": 0,
        "archived_in_office": 0,
        "ready_for_pickup": 0,
        "returned": 0,
    }


def test_list_binders_enriched_returns_counters_for_all_statuses(test_db, test_user):
    c1, _c2, b1, b2 = _seed_binders(test_db, test_user.id)
    returned = Binder(
        client_record_id=c1.id,
        binder_number="AA-300",
        period_start=date.today() - timedelta(days=1),
        status=BinderStatus.RETURNED,
        returned_at=date.today(),
        created_by=test_user.id,
    )
    test_db.add(returned)
    test_db.commit()

    service = BinderListService()
    service.db = test_db
    service.binder_repo = BinderRepository(test_db)
    service.client_record_repo = ClientRecordRepository(test_db)

    items, total, counters = service.list_binders_enriched()

    assert total == 2
    assert {item.id for item in items} == {b1.id, b2.id}
    assert counters == {
        "total": 3,
        "in_office": 1,
        "closed_in_office": 0,
        "archived_in_office": 0,
        "ready_for_pickup": 1,
        "returned": 1,
    }


def test_get_binder_with_client_name_returns_none_for_missing(test_db, test_user):
    _seed_binders(test_db, test_user.id)
    service = BinderListService()
    service.db = test_db
    service.binder_repo = BinderRepository(test_db)
    service.client_record_repo = ClientRecordRepository(test_db)

    assert service.get_binder_with_client_name(999999) is None


def test_build_binder_response_handles_null_period_start(test_db, test_user):
    client = seed_client_identity(test_db, full_name="Null Period Client", id_number="BLSNULL")

    binder = Binder(
        client_record_id=client.id,
        binder_number="NULL-100",
        period_start=None,
        status=BinderStatus.IN_OFFICE,
        created_by=test_user.id,
    )
    test_db.add(binder)
    test_db.commit()
    test_db.refresh(binder)

    service = BinderListService()
    service.db = test_db
    service.binder_repo = BinderRepository(test_db)
    service.client_record_repo = ClientRecordRepository(test_db)

    response = service.build_binder_response(binder, client_name=client.full_name)

    assert response.period_start is None
    assert response.days_in_office is None
