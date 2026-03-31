from datetime import date, timedelta

from app.binders.models.binder import Binder, BinderStatus
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.services.binder_list_service import BinderListService
from app.clients.models import Client
from app.clients.repositories.client_repository import ClientRepository


def _seed_binders(db, user_id: int):
    c1 = Client(
        full_name="Alpha Client",
        id_number="BLS001",
    )
    c2 = Client(
        full_name="Beta Client",
        id_number="BLS002",
    )
    db.add_all([c1, c2])
    db.commit()
    db.refresh(c1)
    db.refresh(c2)

    b1 = Binder(
        client_id=c1.id,
        binder_number="AA-100",
        period_start=date.today() - timedelta(days=15),
        status=BinderStatus.IN_OFFICE,
        created_by=user_id,
    )
    b2 = Binder(
        client_id=c2.id,
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


def test_list_binders_enriched_filters_and_invalid_sort_dir(monkeypatch, test_db, test_user):
    c1, c2, _b1, _b2 = _seed_binders(test_db, test_user.id)
    service = BinderListService()
    service.db = test_db
    service.binder_repo = BinderRepository(test_db)
    service.client_repo = ClientRepository(test_db)

    monkeypatch.setattr(
        "app.binders.services.binder_list_service.SignalsService.compute_binder_signals",
        lambda self, binder, ref_date: ["idle_binder"] if binder.client_id == c1.id else [],
    )

    items, total = service.list_binders_enriched(
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

    none_items, none_total = service.list_binders_enriched(query="does-not-match")
    assert none_total == 0
    assert none_items == []


def test_get_binder_with_client_name_returns_none_for_missing(test_db, test_user):
    _seed_binders(test_db, test_user.id)
    service = BinderListService()
    service.db = test_db
    service.binder_repo = BinderRepository(test_db)
    service.client_repo = ClientRepository(test_db)

    assert service.get_binder_with_client_name(999999) is None
