from datetime import date, datetime
from types import SimpleNamespace

from app.binders.models.binder import BinderStatus
from app.dashboard.services.dashboard_extended_service import DashboardExtendedService
from app.users.models.user import UserRole


def test_get_attention_items_returns_idle_and_ready_items(test_db, monkeypatch):
    service = DashboardExtendedService(test_db)
    ready_binder = SimpleNamespace(
        id=2,
        client_record_id=12,
        binder_number="READY-1",
        period_start=date(2026, 2, 15),
        status=BinderStatus.READY_FOR_PICKUP,
    )
    business_ready = SimpleNamespace(id=12, full_name="Ready Client")

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
        client_record_id=13,
        binder_number="NOATTN",
        period_start=date(2026, 2, 15),
        status=BinderStatus.IN_OFFICE,
    )
    business_obj = SimpleNamespace(id=13, full_name="No Attention")
    monkeypatch.setattr(service, "_active_binders_with_businesses", lambda: [(binder, business_obj)])
    service.charge_repo = SimpleNamespace(
        list_charges=lambda **kwargs: [
            SimpleNamespace(business_id=999, client_record_id=999, id=1, amount=10)
        ]
    )
    service.business_repo = SimpleNamespace(list_by_ids=lambda ids: [])

    items = service.get_attention_items(user_role=UserRole.ADVISOR, reference_date=date(2026, 3, 10))
    assert items == []


def test_get_attention_items_advisor_appends_unpaid_charge_item(test_db, monkeypatch):
    service = DashboardExtendedService(test_db)
    binder = SimpleNamespace(
        id=5,
        client_record_id=20,
        binder_number="NORM-1",
        period_start=date(2026, 2, 1),
        status=BinderStatus.IN_OFFICE,
    )
    business = SimpleNamespace(id=20, full_name="Mapped Business")
    mapped_charge_business = SimpleNamespace(id=77, business_name="Charge Business")
    charge = SimpleNamespace(
        id=4,
        client_record_id=88,
        business_id=77,
        amount=300,
        charge_type="monthly_retainer",
        description=None,
        issued_at=datetime(2026, 3, 12, 10, 30),
        invoice=None,
        period="2026-02",
    )
    client_record = SimpleNamespace(id=88, legal_entity_id=99)
    legal_entity = SimpleNamespace(id=99, official_name="Legal Client")

    monkeypatch.setattr(service, "_active_binders_with_businesses", lambda: [(binder, business)])
    service.charge_repo = SimpleNamespace(list_charges=lambda **kwargs: [charge])
    service.business_repo = SimpleNamespace(list_by_ids=lambda ids: [mapped_charge_business])
    service.client_record_repo = SimpleNamespace(list_by_ids=lambda ids: [client_record])
    service.legal_entity_repo = SimpleNamespace(get_by_id=lambda legal_entity_id: legal_entity)

    items = service.get_attention_items(user_role=UserRole.ADVISOR, reference_date=date(2026, 3, 10))

    assert len(items) == 1
    assert items[0]["item_type"] == "unpaid_charge"
    assert items[0]["client_name"] == "Legal Client"
    assert items[0]["description"] == "Charge Business · ₪300 · לתשלום היום"
    assert items[0]["charge_subject"] == "חשבונית #4 · ריטיינר חודשי · תקופה 02/2026"
    assert items[0]["charge_date"] == date(2026, 3, 12)
    assert items[0]["charge_amount"] == "₪300"
    assert items[0]["charge_invoice_number"] == "4"
    assert items[0]["charge_period"] == "2026-02"
