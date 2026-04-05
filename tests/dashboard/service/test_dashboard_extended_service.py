from datetime import date
from types import SimpleNamespace

from app.binders.models.binder import BinderStatus
from app.dashboard.services.dashboard_extended_service import DashboardExtendedService
from app.users.models.user import UserRole


def test_get_attention_items_returns_idle_and_ready_items(test_db, monkeypatch):
    service = DashboardExtendedService(test_db)
    ready_binder = SimpleNamespace(
        id=2,
        client_id=12,
        binder_number="READY-1",
        period_start=date(2026, 2, 15),
        status=BinderStatus.READY_FOR_PICKUP,
    )
    business_ready = SimpleNamespace(id=12, client_id=12, full_name="Ready Client")

    monkeypatch.setattr(
        service,
        "_active_binders_with_businesses",
        lambda: [(ready_binder, business_ready)],
    )

    items = service.get_attention_items(user_role=None, reference_date=date(2026, 3, 10))
    item_types = [item["item_type"] for item in items]
    assert item_types == ["ready_for_pickup"]


def test_get_attention_items_advisor_skips_unmapped_charge_clients(test_db, monkeypatch):
    service = DashboardExtendedService(test_db)
    binder = SimpleNamespace(
        id=3,
        client_id=13,
        binder_number="NOATTN",
        period_start=date(2026, 2, 15),
        status=BinderStatus.IN_OFFICE,
    )
    business_obj = SimpleNamespace(id=13, client_id=13, full_name="No Attention")
    monkeypatch.setattr(service, "_active_binders_with_businesses", lambda: [(binder, business_obj)])
    service.charge_repo = SimpleNamespace(
        list_charges=lambda **kwargs: [SimpleNamespace(business_id=999, id=1, amount=10)]
    )
    service.business_repo = SimpleNamespace(list_by_ids=lambda ids: [])

    items = service.get_attention_items(user_role=UserRole.ADVISOR, reference_date=date(2026, 3, 10))
    assert items == []


def test_get_attention_items_advisor_appends_unpaid_charge_item(test_db, monkeypatch):
    service = DashboardExtendedService(test_db)
    binder = SimpleNamespace(
        id=5,
        client_id=20,
        binder_number="NORM-1",
        period_start=date(2026, 2, 1),
        status=BinderStatus.IN_OFFICE,
    )
    business = SimpleNamespace(id=20, client_id=20, full_name="Mapped Business")
    mapped_charge_business = SimpleNamespace(id=77, client_id=77, full_name="Charge Business")
    charge = SimpleNamespace(id=4, business_id=77, amount=300)

    monkeypatch.setattr(service, "_active_binders_with_businesses", lambda: [(binder, business)])
    service.charge_repo = SimpleNamespace(list_charges=lambda **kwargs: [charge])
    service.business_repo = SimpleNamespace(list_by_ids=lambda ids: [mapped_charge_business])

    items = service.get_attention_items(user_role=UserRole.ADVISOR, reference_date=date(2026, 3, 10))

    assert len(items) == 1
    assert items[0]["item_type"] == "unpaid_charge"
    assert items[0]["client_name"] == "Charge Business"
    assert items[0]["description"] == "חיוב לא משולם: ₪300"
